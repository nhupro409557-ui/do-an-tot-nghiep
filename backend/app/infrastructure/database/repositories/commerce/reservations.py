from datetime import datetime
from decimal import Decimal
import json
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AIContextLog,
    LoyaltyTransaction,
    Order,
    OrderHistoryLog,
    OrderItem,
    PaymentTransaction,
    Product,
    User,
    UserVoucher,
    Voucher,
)


async def get_order_by_idempotency_key(session: AsyncSession, idempotency_key: str) -> Order | None:
    return await session.scalar(select(Order).where(Order.idempotency_key == idempotency_key))


async def get_user_for_update(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.scalar(select(User).where(User.id == user_id).with_for_update())


async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.scalar(select(User).where(User.id == user_id))


async def list_product_categories(session: AsyncSession, product_ids: list[UUID]) -> list:
    result = await session.execute(
        select(Product.id, Product.category_id, Product.subcategory_id, Product.brand_id).where(Product.id.in_(product_ids))
    )
    return list(result)


async def get_variant_inventory_for_update(
    session: AsyncSession,
    *,
    variant_id: UUID,
    product_id: UUID | None,
    for_update: bool = True,
) -> dict | None:
    lock_clause = "FOR UPDATE OF pv, p" if for_update else ""
    row = (
        await session.execute(
            text(
                f"""
                SELECT
                    pv.id,
                    pv.product_id,
                    pv.stock_quantity,
                    p.name AS product_name,
                    pv.color_name,
                    pv.storage,
                    pv.ram,
                    pv.configuration,
                    p.category_id,
                    p.subcategory_id,
                    p.brand_id,
                    GREATEST(COALESCE(p.warranty_period, 0), 0) AS warranty_months_snapshot,
                    COALESCE(NULLIF(pv.sale_price, 0), NULLIF(pv.price, 0), NULLIF(p.sale_price, 0), p.price, 0) AS regular_unit_price,
                    COALESCE(vfs.id, fs.id)::text AS flash_sale_id,
                    COALESCE(vfs.discount_type, fs.discount_type) AS flash_sale_discount_type,
                    COALESCE(vfs.discount_value, fs.discount_value) AS flash_sale_discount_value,
                    COALESCE(vfs.quantity_limit, fs.quantity_limit) AS flash_sale_quantity_limit,
                    COALESCE(vfs.sold_quantity, fs.sold_quantity) AS flash_sale_sold_quantity,
                    COALESCE(vfs.per_user_limit, fs.per_user_limit) AS flash_sale_per_user_limit,
                    CASE
                        WHEN COALESCE(vfs.quantity_limit, fs.quantity_limit) IS NULL THEN NULL
                        ELSE GREATEST(COALESCE(vfs.quantity_limit, fs.quantity_limit) - COALESCE(vfs.sold_quantity, fs.sold_quantity), 0)
                    END AS flash_sale_remaining_quantity
                FROM product_variants pv
                JOIN products p ON p.id = pv.product_id
                LEFT JOIN categories c ON c.id = COALESCE(p.subcategory_id, p.category_id)
                LEFT JOIN brands b ON b.id = p.brand_id
                LEFT JOIN LATERAL (
                    SELECT id, discount_type, discount_value, quantity_limit, sold_quantity, per_user_limit
                    FROM flash_sales
                    WHERE product_id = p.id
                      AND variant_id = pv.id
                      AND status = 'ACTIVE'
                      AND (starts_at IS NULL OR starts_at <= NOW())
                      AND (ends_at IS NULL OR ends_at >= NOW())
                      AND (quantity_limit IS NULL OR sold_quantity < quantity_limit)
                    ORDER BY updated_at DESC
                    LIMIT 1
                ) vfs ON TRUE
                LEFT JOIN LATERAL (
                    SELECT id, discount_type, discount_value, quantity_limit, sold_quantity, per_user_limit
                    FROM flash_sales
                    WHERE product_id = p.id
                      AND variant_id IS NULL
                      AND status = 'ACTIVE'
                      AND (starts_at IS NULL OR starts_at <= NOW())
                      AND (ends_at IS NULL OR ends_at >= NOW())
                      AND (quantity_limit IS NULL OR sold_quantity < quantity_limit)
                    ORDER BY updated_at DESC
                    LIMIT 1
                ) fs ON TRUE
                WHERE pv.id = CAST(:variant_id AS uuid)
                  AND (CAST(:product_id AS uuid) IS NULL OR pv.product_id = CAST(:product_id AS uuid))
                  AND pv.is_active = TRUE
                  AND pv.deleted_at IS NULL
                  AND LOWER(COALESCE(pv.status, 'active')) = 'active'
                  AND p.status = 'ACTIVE'
                  AND p.deleted_at IS NULL
                  AND COALESCE(p.hidden_by_category, FALSE) = FALSE
                  AND COALESCE(p.hidden_by_brand, FALSE) = FALSE
                  AND (c.id IS NULL OR (c.status = 'ACTIVE' AND COALESCE(c.is_active, TRUE) = TRUE AND COALESCE(c.is_deleted, FALSE) = FALSE))
                  AND (b.id IS NULL OR COALESCE(b.is_active, TRUE) = TRUE)
                {lock_clause}
                """
            ),
            {"variant_id": variant_id, "product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_product_inventory_for_update(
    session: AsyncSession,
    product_id: UUID,
    *,
    for_update: bool = True,
) -> dict | None:
    lock_clause = "FOR UPDATE OF p" if for_update else ""
    row = (
        await session.execute(
            text(
                f"""
                SELECT
                    p.id,
                    p.stock_quantity,
                    p.name AS product_name,
                    p.category_id,
                    p.subcategory_id,
                    p.brand_id,
                    GREATEST(COALESCE(p.warranty_period, 0), 0) AS warranty_months_snapshot,
                    COALESCE(NULLIF(p.sale_price, 0), p.price, 0) AS regular_unit_price,
                    fs.id::text AS flash_sale_id,
                    fs.discount_type AS flash_sale_discount_type,
                    fs.discount_value AS flash_sale_discount_value,
                    fs.quantity_limit AS flash_sale_quantity_limit,
                    fs.sold_quantity AS flash_sale_sold_quantity,
                    fs.per_user_limit AS flash_sale_per_user_limit,
                    CASE
                        WHEN fs.quantity_limit IS NULL THEN NULL
                        ELSE GREATEST(fs.quantity_limit - fs.sold_quantity, 0)
                    END AS flash_sale_remaining_quantity
                FROM products p
                LEFT JOIN categories c ON c.id = COALESCE(p.subcategory_id, p.category_id)
                LEFT JOIN brands b ON b.id = p.brand_id
                LEFT JOIN LATERAL (
                    SELECT id, discount_type, discount_value, quantity_limit, sold_quantity, per_user_limit
                    FROM flash_sales
                    WHERE product_id = p.id
                      AND variant_id IS NULL
                      AND status = 'ACTIVE'
                      AND (starts_at IS NULL OR starts_at <= NOW())
                      AND (ends_at IS NULL OR ends_at >= NOW())
                      AND (quantity_limit IS NULL OR sold_quantity < quantity_limit)
                    ORDER BY updated_at DESC
                    LIMIT 1
                ) fs ON TRUE
                WHERE p.id = :product_id
                  AND p.status = 'ACTIVE'
                  AND p.deleted_at IS NULL
                  AND COALESCE(p.hidden_by_category, FALSE) = FALSE
                  AND COALESCE(p.hidden_by_brand, FALSE) = FALSE
                  AND (c.id IS NULL OR (c.status = 'ACTIVE' AND COALESCE(c.is_active, TRUE) = TRUE AND COALESCE(c.is_deleted, FALSE) = FALSE))
                  AND (b.id IS NULL OR COALESCE(b.is_active, TRUE) = TRUE)
                {lock_clause}
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_variant_stock(session: AsyncSession, *, variant_id: UUID, quantity: int) -> None:
    await session.execute(
        text("UPDATE product_variants SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
        {"id": variant_id, "quantity": quantity},
    )


async def update_product_stock(session: AsyncSession, *, product_id: UUID, quantity: int) -> None:
    await session.execute(
        text("UPDATE products SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
        {"id": product_id, "quantity": quantity},
    )

async def get_active_reserved_quantity(
    session: AsyncSession,
    *,
    product_id: UUID | None,
    variant_id: UUID | None,
) -> int:
    result = await session.execute(
        text(
            """
            SELECT COALESCE(SUM(reserved_quantity), 0)::int
            FROM inventory_reservations
            WHERE status = 'ACTIVE'
              AND (expires_at IS NULL OR expires_at > NOW())
              AND product_id IS NOT DISTINCT FROM :product_id
              AND variant_id IS NOT DISTINCT FROM :variant_id
            """
        ),
        {"product_id": product_id, "variant_id": variant_id},
    )
    return int(result.scalar() or 0)


async def get_main_inventory_location_id(session: AsyncSession) -> UUID:
    result = await session.execute(
        text(
            """
            SELECT id
            FROM inventory_locations
            WHERE code = 'MAIN'
            ORDER BY created_at ASC
            LIMIT 1
            """
        )
    )
    location_id = result.scalar_one_or_none()
    if location_id:
        return location_id

    new_location_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO inventory_locations (id, code, name, type, is_active)
            VALUES (:id, 'MAIN', 'Kho chính', 'WAREHOUSE', TRUE)
            """
        ),
        {"id": new_location_id},
    )
    return new_location_id


async def create_inventory_reservation(
    session: AsyncSession,
    *,
    order_id: UUID,
    order_code: str,
    product_id: UUID | None,
    variant_id: UUID | None,
    quantity: int,
) -> None:
    location_id = await get_main_inventory_location_id(session)
    reservation_code = f"ORDER-{order_code}-{variant_id or product_id}"

    # Lock the product/variant to prevent race conditions on dynamic creation
    if variant_id:
        p_row = (await session.execute(
            text("SELECT stock_quantity FROM product_variants WHERE id = :variant_id FOR UPDATE"),
            {"variant_id": variant_id}
        )).mappings().first()
    else:
        p_row = (await session.execute(
            text("SELECT stock_quantity FROM products WHERE id = :product_id FOR UPDATE"),
            {"product_id": product_id}
        )).mappings().first()

    if not p_row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")

    stock_quantity = int(p_row["stock_quantity"] or 0)

    # Check for existing reservation to handle idempotency safely
    existing = (await session.execute(
        text("SELECT id, reserved_quantity, status FROM inventory_reservations WHERE reservation_code = :code"),
        {"code": reservation_code}
    )).mappings().first()

    if existing and existing["status"] == "ACTIVE":
        diff = quantity - int(existing["reserved_quantity"] or 0)
        if diff != 0:
            if variant_id:
                level_row = (await session.execute(
                    text("SELECT id, on_hand_quantity, reserved_quantity FROM inventory_levels WHERE location_id = :location_id AND product_id IS NULL AND variant_id = :variant_id FOR UPDATE"),
                    {"location_id": location_id, "variant_id": variant_id}
                )).mappings().first()
            else:
                level_row = (await session.execute(
                    text("SELECT id, on_hand_quantity, reserved_quantity FROM inventory_levels WHERE location_id = :location_id AND product_id = :product_id AND variant_id IS NULL FOR UPDATE"),
                    {"location_id": location_id, "product_id": product_id}
                )).mappings().first()

            if not level_row:
                if stock_quantity >= diff:
                    await session.execute(
                        text(
                            """
                            INSERT INTO inventory_levels (
                                id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost
                            )
                            VALUES (:id, :product_id, :variant_id, :location_id, :on_hand_quantity, :reserved_quantity, 0)
                            """
                        ),
                        {
                            "id": uuid4(),
                            "product_id": product_id if variant_id is None else None,
                            "variant_id": variant_id,
                            "location_id": location_id,
                            "on_hand_quantity": stock_quantity,
                            "reserved_quantity": max(diff, 0),
                        }
                    )
                else:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=409, detail="Tồn khả dụng không đủ để giữ hàng.")
            else:
                res = await session.execute(
                    text(
                        """
                        UPDATE inventory_levels
                        SET reserved_quantity = reserved_quantity + :diff,
                            updated_at = NOW()
                        WHERE id = :id
                          AND (:diff <= 0 OR on_hand_quantity - reserved_quantity >= :diff)
                        RETURNING id
                        """
                    ),
                    {"id": level_row["id"], "diff": diff},
                )
                if not res.rowcount:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=409, detail="Tồn khả dụng không đủ để giữ hàng.")
    else:
        # If it was inactive or new reservation
        if variant_id:
            level_row = (await session.execute(
                text("SELECT id, on_hand_quantity, reserved_quantity FROM inventory_levels WHERE location_id = :location_id AND product_id IS NULL AND variant_id = :variant_id FOR UPDATE"),
                {"location_id": location_id, "variant_id": variant_id}
            )).mappings().first()
        else:
            level_row = (await session.execute(
                text("SELECT id, on_hand_quantity, reserved_quantity FROM inventory_levels WHERE location_id = :location_id AND product_id = :product_id AND variant_id IS NULL FOR UPDATE"),
                {"location_id": location_id, "product_id": product_id}
            )).mappings().first()

        if not level_row:
            if stock_quantity >= quantity:
                await session.execute(
                    text(
                        """
                        INSERT INTO inventory_levels (
                            id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost
                        )
                        VALUES (:id, :product_id, :variant_id, :location_id, :on_hand_quantity, :reserved_quantity, 0)
                        """
                    ),
                    {
                        "id": uuid4(),
                        "product_id": product_id if variant_id is None else None,
                        "variant_id": variant_id,
                        "location_id": location_id,
                        "on_hand_quantity": stock_quantity,
                        "reserved_quantity": quantity,
                    }
                )
            else:
                from fastapi import HTTPException
                raise HTTPException(status_code=409, detail="Tồn khả dụng không đủ để giữ hàng.")
        else:
            res = await session.execute(
                text(
                    """
                    UPDATE inventory_levels
                    SET reserved_quantity = reserved_quantity + :quantity,
                        updated_at = NOW()
                    WHERE id = :id
                      AND on_hand_quantity - reserved_quantity >= :quantity
                    RETURNING id
                    """
                ),
                {"id": level_row["id"], "quantity": quantity},
            )
            if not res.rowcount:
                from fastapi import HTTPException
                raise HTTPException(status_code=409, detail="Tồn khả dụng không đủ để giữ hàng.")

    await session.execute(
        text(
            """
            INSERT INTO inventory_reservations (
                id, product_id, variant_id, location_id, order_id,
                reservation_code, reserved_quantity, status, expires_at
            )
            VALUES (
                :id, :product_id, :variant_id, :location_id, :order_id,
                :reservation_code, :reserved_quantity, 'ACTIVE', NOW() + INTERVAL '24 hours'
            )
            ON CONFLICT (reservation_code) DO UPDATE
            SET reserved_quantity = EXCLUDED.reserved_quantity,
                status = 'ACTIVE',
                expires_at = EXCLUDED.expires_at,
                released_at = NULL
            """
        ),
        {
            "id": uuid4(),
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "order_id": order_id,
            "reservation_code": reservation_code,
            "reserved_quantity": quantity,
        },
    )


async def close_active_order_reservations(session: AsyncSession, *, order_id: UUID, status: str) -> None:
    if status not in {"CONSUMED", "RELEASED", "EXPIRED", "CANCELLED"}:
        return

    # 1. Đối soát và kiểm tra lệch tồn kho trước khi cập nhật
    check_res = await session.execute(
        text(
            """
            SELECT il.product_id, il.variant_id, il.on_hand_quantity, il.reserved_quantity, r.reserved_quantity AS req_quantity, loc.code AS loc_code
            FROM inventory_reservations r
            JOIN inventory_levels il ON il.location_id = r.location_id
              AND il.product_id IS NOT DISTINCT FROM r.product_id
              AND il.variant_id IS NOT DISTINCT FROM r.variant_id
            JOIN inventory_locations loc ON loc.id = r.location_id
            WHERE r.order_id = :order_id AND r.status = 'ACTIVE'
            FOR UPDATE OF r, il
            """
        ),
        {"order_id": order_id},
    )
    rows = check_res.mappings().all()
    if not rows:
        return

    from fastapi import HTTPException
    for row in rows:
        # Kiểm tra lượng reserved_quantity trong kho có đủ để giải phóng / tiêu thụ không
        if row["reserved_quantity"] < row["req_quantity"]:
            raise HTTPException(
                status_code=409,
                detail=f"Lỗi lệch tồn kho đặt trước (lượng đang giữ: {row['reserved_quantity']}, yêu cầu giải phóng: {row['req_quantity']}).",
            )
        # Nếu là CONSUMED thì phải trừ on_hand_quantity tại kho MAIN
        if status == "CONSUMED" and row["loc_code"] == "MAIN":
            if row["on_hand_quantity"] < row["req_quantity"]:
                raise HTTPException(
                    status_code=409,
                    detail=f"Không đủ tồn kho thực tế để hoàn tất xuất hàng (hiện có: {row['on_hand_quantity']}, yêu cầu xuất: {row['req_quantity']}).",
                )

    # 2. Cập nhật tồn kho (đã đảm bảo không bị âm nhờ bước check ở trên)
    result = await session.execute(
        text("""
            UPDATE inventory_levels il
            SET reserved_quantity = il.reserved_quantity - r.reserved_quantity,
                on_hand_quantity = CASE
                    WHEN :status = 'CONSUMED' AND loc.code = 'MAIN'
                        THEN il.on_hand_quantity - r.reserved_quantity
                    ELSE il.on_hand_quantity
                END,
                updated_at = NOW()
            FROM inventory_reservations r
            JOIN inventory_locations loc ON loc.id = r.location_id
            WHERE r.order_id = :order_id
              AND r.status = 'ACTIVE'
              AND il.location_id = r.location_id
              AND il.product_id IS NOT DISTINCT FROM r.product_id
              AND il.variant_id IS NOT DISTINCT FROM r.variant_id
              AND il.reserved_quantity >= r.reserved_quantity
              AND (
                  :status <> 'CONSUMED'
                  OR loc.code <> 'MAIN'
                  OR il.on_hand_quantity >= r.reserved_quantity
              )
        """),
        {"order_id": order_id, "status": status},
    )
    if int(result.rowcount or 0) != len(rows):
        raise HTTPException(
            status_code=409,
            detail="Tồn kho đặt trước đã thay đổi trong lúc xử lý. Vui lòng thử lại thao tác.",
        )

    # 3. Cập nhật trạng thái của các reservations
    await session.execute(
        text(
            """
            UPDATE inventory_reservations
            SET status = :status,
                released_at = NOW()
            WHERE order_id = :order_id
              AND status = 'ACTIVE'
            """
        ),
        {"order_id": order_id, "status": status},
    )


async def release_inventory_level_reservation(session: AsyncSession, *, reservation_id: UUID) -> None:
    # 1. Update inventory_levels
    await session.execute(
        text(
            """
            UPDATE inventory_levels il
            SET reserved_quantity = GREATEST(il.reserved_quantity - r.reserved_quantity, 0),
                updated_at = NOW()
            FROM inventory_reservations r
            WHERE r.id = :reservation_id
              AND il.location_id = r.location_id
              AND il.product_id IS NOT DISTINCT FROM r.product_id
              AND il.variant_id IS NOT DISTINCT FROM r.variant_id
              AND r.status = 'ACTIVE'
            """
        ),
        {"reservation_id": reservation_id},
    )

    # 2. Update status of the single reservation
    await session.execute(
        text(
            """
            UPDATE inventory_reservations
            SET status = 'RELEASED',
                released_at = NOW()
            WHERE id = :reservation_id
              AND status = 'ACTIVE'
            """
        ),
        {"reservation_id": reservation_id},
    )


async def order_has_inventory_adjustment_reason(
    session: AsyncSession,
    *,
    order_code: str,
    reason: str,
) -> bool:
    result = await session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM inventory_adjustment_logs
                WHERE reference_code = :order_code
                  AND reason = :reason
            )
            """
        ),
        {"order_code": order_code, "reason": reason},
    )
    return bool(result.scalar())


async def insert_inventory_adjustment(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    old_quantity: int,
    new_quantity: int,
    delta: int,
    transaction_type: str,
    reference_code: str,
    reason: str,
    note: str,
    location_code: str | None = None,
    location_name: str | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_adjustment_logs (
                id, product_id, variant_id, old_quantity, new_quantity, delta,
                transaction_type, reference_code, reason, note, location_code, location_name
            )
            VALUES (
                :id, :product_id, :variant_id, :old_quantity, :new_quantity, :delta,
                :transaction_type, :reference_code, :reason, :note, :location_code, :location_name
            )
            """
        ),
        {
            "id": uuid4(),
            "product_id": product_id,
            "variant_id": variant_id,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "delta": delta,
            "transaction_type": transaction_type,
            "reference_code": reference_code,
            "reason": reason,
            "note": note,
            "location_code": location_code,
            "location_name": location_name,
        },
    )


async def decrement_variant_stock(session: AsyncSession, *, variant_id: UUID, quantity: int) -> None:
    from fastapi import HTTPException
    result = await session.execute(
        text("""
            UPDATE product_variants
            SET stock_quantity = stock_quantity - :quantity, updated_at = NOW()
            WHERE id = :id AND stock_quantity >= :quantity
        """),
        {"id": variant_id, "quantity": quantity},
    )
    if result.rowcount != 1:
        raise HTTPException(status_code=409, detail="Không đủ tồn kho biến thể để xuất hàng.")


async def decrement_product_stock(session: AsyncSession, *, product_id: UUID, quantity: int) -> None:
    from fastapi import HTTPException
    result = await session.execute(
        text("""
            UPDATE products
            SET stock_quantity = stock_quantity - :quantity, updated_at = NOW()
            WHERE id = :id AND stock_quantity >= :quantity
        """),
        {"id": product_id, "quantity": quantity},
    )
    if result.rowcount != 1:
        raise HTTPException(status_code=409, detail="Không đủ tồn kho sản phẩm để xuất hàng.")
