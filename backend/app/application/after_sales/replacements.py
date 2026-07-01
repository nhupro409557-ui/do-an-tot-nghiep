from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import after_sales_repo


async def complete_replacement(
    session: AsyncSession,
    *,
    kind: str,
    request: dict,
    request_id: UUID,
    items: list[dict],
    replacement_imei: str,
    actor_id: UUID,
) -> None:
    if len(items) != 1:
        raise HTTPException(status_code=400, detail="Quét IMEI thay thế hiện hỗ trợ từng sản phẩm một.")
    item = items[0]
    new_identifier = await session.execute(
        text(
            """
            SELECT id, status, location_id FROM product_imeis
            WHERE imei=:imei AND product_id=:product_id
              AND variant_id IS NOT DISTINCT FROM :variant_id
            FOR UPDATE
            """
        ),
        {
            "imei": replacement_imei,
            "product_id": item["product_id"],
            "variant_id": item["product_variant_id"],
        },
    )
    row = new_identifier.first()
    if not row or row.status != "IN_STOCK":
        raise HTTPException(status_code=409, detail="IMEI thay thế không còn ở trạng thái sẵn sàng trong kho.")
    level = (await session.execute(
        text(
            """
            SELECT id, on_hand_quantity
            FROM inventory_levels
            WHERE location_id=:location_id
              AND ((:variant_id IS NOT NULL AND variant_id=:variant_id)
                   OR (:variant_id IS NULL AND product_id=:product_id))
            FOR UPDATE
            """
        ),
        {
            "location_id": row.location_id,
            "variant_id": item["product_variant_id"],
            "product_id": item["product_id"],
        },
    )).first()
    if not level or level.on_hand_quantity < 1:
        raise HTTPException(status_code=409, detail="Tồn kho vật lý tại vị trí của IMEI không đủ để xuất đổi.")
    await session.execute(
        text("UPDATE inventory_levels SET on_hand_quantity=on_hand_quantity-1, updated_at=NOW() WHERE id=:id"),
        {"id": level.id},
    )
    if item["product_variant_id"]:
        await session.execute(
            text("UPDATE product_variants SET stock_quantity=GREATEST(stock_quantity-1,0), updated_at=NOW() WHERE id=:id"),
            {"id": item["product_variant_id"]},
        )
    await session.execute(
        text("UPDATE products SET stock_quantity=GREATEST(stock_quantity-1,0), updated_at=NOW() WHERE id=:id"),
        {"id": item["product_id"]},
    )
    await session.execute(
        text(
            """
            INSERT INTO inventory_adjustment_logs
                (id, product_id, variant_id, old_quantity, new_quantity, delta, reason, note)
            VALUES
                (:id, :product_id, :variant_id, :old_quantity, :new_quantity, -1,
                 'AFTER_SALES_REPLACEMENT', :note)
            """
        ),
        {
            "id": uuid4(),
            "product_id": item["product_id"],
            "variant_id": item["product_variant_id"],
            "old_quantity": level.on_hand_quantity,
            "new_quantity": level.on_hand_quantity - 1,
            "note": f"Xuất máy thay thế cho yêu cầu {kind} {request_id}.",
        },
    )
    await session.execute(
        text("UPDATE product_imeis SET status='SOLD', sold_at=NOW(), sold_order_id=:order_id, updated_at=NOW() WHERE id=:id"),
        {"id": row.id, "order_id": request["order_id"]},
    )
    if item.get("imei"):
        await session.execute(
            text("UPDATE product_imeis SET status='DEFECTIVE_RETURNED', updated_at=NOW() WHERE imei=:imei"),
            {"imei": item["imei"]},
        )
    await session.execute(
        text(
            """
            UPDATE after_sales_allocations SET status='CONSUMED', consumed_at=NOW()
            WHERE reference_type=:kind AND reference_id=:request_id AND status='LOCKED'
            """
        ),
        {"kind": kind, "request_id": request_id},
    )
    _, item_table = after_sales_repo._table(kind)
    await session.execute(
        text(f"UPDATE {item_table} SET replacement_imei=:imei WHERE request_id=:id"),
        {"imei": replacement_imei, "id": request_id},
    )
    if item.get("imei"):
        old_id = await session.scalar(text("SELECT id FROM product_imeis WHERE imei=:imei"), {"imei": item["imei"]})
        if old_id:
            await session.execute(
                text(
                    """
                    INSERT INTO imei_disposition_events
                        (id, imei_id, after_sales_type, after_sales_id, old_status,
                         new_status, reason, actor_id)
                    VALUES (:id, :imei_id, :kind, :request_id, 'SOLD',
                            'DEFECTIVE_RETURNED', 'Thu hồi từ yêu cầu hậu mãi.', :actor_id)
                    """
                ),
                {
                    "id": uuid4(),
                    "imei_id": old_id,
                    "kind": kind,
                    "request_id": request_id,
                    "actor_id": actor_id,
                },
            )
