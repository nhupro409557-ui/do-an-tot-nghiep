import csv
import io
import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_permission
from app.api.v1.routers.admin_categories import ensure_categories_not_migrating
from app.api.v1.routers.admin_product_utils import persisted_sales_config, sync_parent_price_from_variants
from app.api.v1.routers.admin_schemas import InventoryAdjustmentPayload, InventorySettingsPayload, VariantInventoryPayload
from app.api.v1.routers.admin_utils import generate_inventory_imei
from app.infrastructure.database.session import get_session


router = APIRouter()

@router.get("/products/{product_id}/inventory", dependencies=[Depends(require_permission("inventory:read"))])
async def get_product_inventory(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    product = (
        await session.execute(
            text(
                """
                SELECT id::text, name, sku, stock_quantity AS stock,
                       stock_quantity AS "stockQuantity",
                       CASE WHEN stock_quantity > 0 THEN 'IN_STOCK' ELSE 'OUT_OF_STOCK' END AS "stockState",
                       sales_config AS "salesConfig"
                FROM products
                WHERE id = :id
                """
            ),
            {"id": product_id},
        )
    ).mappings().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    variants = (
        await session.execute(
            text(
                """
                SELECT id::text, sku, color_name AS "colorName", configuration,
                       stock_quantity AS "stockQuantity",
                       CASE WHEN stock_quantity > 0 THEN 'IN_STOCK' ELSE 'OUT_OF_STOCK' END AS "stockState",
                       is_active AS "isActive"
                FROM product_variants
                WHERE product_id = :product_id AND deleted_at IS NULL
                ORDER BY created_at, sku
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().all()
    logs = (
        await session.execute(
            text(
                """
                SELECT id::text, product_id::text AS "productId", variant_id::text AS "variantId",
                       old_quantity AS "oldQuantity", new_quantity AS "newQuantity",
                       delta, transaction_type AS "transactionType",
                       reference_code AS "referenceCode", reason, note,
                       supplier_name AS "supplierName", unit_cost AS "unitCost",
                       location_code AS "locationCode", location_name AS "locationName",
                       created_at AS "createdAt"
                FROM inventory_adjustment_logs
                WHERE product_id = :product_id
                ORDER BY created_at DESC
                LIMIT 20
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().all()
    product_data = dict(product)
    sales_config = product_data.get("salesConfig") if isinstance(product_data.get("salesConfig"), dict) else {}
    minimum_stock = max(0, int(sales_config.get("minimumStock") or 0))
    product_data.update(
        {
            "minimumStock": minimum_stock,
            "blockSaleWhenOutOfStock": bool(sales_config.get("blockSaleWhenOutOfStock", True)),
            "cycleCountDays": int(sales_config.get("cycleCountDays") or 30),
            "stockAlert": "LOW" if int(product_data.get("stockQuantity") or 0) <= minimum_stock else "OK",
        }
    )
    return {**product_data, "variants": [dict(row) for row in variants], "logs": [dict(row) for row in logs]}


@router.patch("/products/{product_id}/inventory/settings", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_product_inventory_settings(
    product_id: UUID,
    payload: InventorySettingsPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    row = (
        await session.execute(
            text("SELECT sales_config FROM products WHERE id = :product_id FOR UPDATE"),
            {"product_id": product_id},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found.")
    sales_config = row.get("sales_config") if isinstance(row.get("sales_config"), dict) else {}
    merged = persisted_sales_config(
        {
            **sales_config,
            "minimumStock": payload.minimumStock,
            "blockSaleWhenOutOfStock": payload.blockSaleWhenOutOfStock,
            "cycleCountDays": payload.cycleCountDays or sales_config.get("cycleCountDays") or 30,
        }
    )
    await session.execute(
        text("UPDATE products SET sales_config = CAST(:sales_config AS jsonb), updated_at = NOW() WHERE id = :product_id"),
        {"product_id": product_id, "sales_config": json.dumps(merged)},
    )
    await session.commit()
    return {"ok": True, **merged}


@router.get("/inventory/export", dependencies=[Depends(require_permission("inventory:read"))])
async def export_inventory_snapshot(
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        text(
            """
            SELECT
                p.id::text AS "productId",
                p.name AS "productName",
                p.sku AS "productSku",
                p.stock_quantity AS "productStock",
                p.status AS "productStatus",
                p.sales_config AS "salesConfig",
                pv.id::text AS "variantId",
                pv.sku AS "variantSku",
                pv.configuration,
                pv.color_name AS "colorName",
                pv.stock_quantity AS "variantStock"
            FROM products p
            LEFT JOIN product_variants pv ON pv.product_id = p.id AND pv.deleted_at IS NULL
            WHERE :search = ''
               OR LOWER(p.name) LIKE LOWER(:pattern)
               OR LOWER(p.sku) LIKE LOWER(:pattern)
               OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
            ORDER BY p.created_at DESC, pv.created_at, pv.sku
            """
        ),
        {"search": search, "pattern": f"%{search}%"},
    )
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "productId",
            "productName",
            "productSku",
            "variantId",
            "variantSku",
            "variantConfiguration",
            "variantColor",
            "stockQuantity",
            "minimumStock",
            "stockAlert",
            "productStatus",
            "blockSaleWhenOutOfStock",
        ],
    )
    writer.writeheader()
    for row in result.mappings().all():
        sales_config = row.get("salesConfig") if isinstance(row.get("salesConfig"), dict) else {}
        minimum_stock = max(0, int(sales_config.get("minimumStock") or 0))
        stock_quantity = int(row.get("variantStock") if row.get("variantId") else row.get("productStock") or 0)
        writer.writerow(
            {
                "productId": row.get("productId"),
                "productName": row.get("productName"),
                "productSku": row.get("productSku"),
                "variantId": row.get("variantId") or "",
                "variantSku": row.get("variantSku") or "",
                "variantConfiguration": row.get("configuration") or "",
                "variantColor": row.get("colorName") or "",
                "stockQuantity": stock_quantity,
                "minimumStock": minimum_stock,
                "stockAlert": "Cần nhập thêm" if stock_quantity <= minimum_stock else "Ổn định",
                "productStatus": row.get("productStatus"),
                "blockSaleWhenOutOfStock": "Có" if sales_config.get("blockSaleWhenOutOfStock", True) else "Không",
            }
        )
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="inventory-export.csv"'},
    )


@router.post("/products/{product_id}/inventory/adjust", dependencies=[Depends(require_permission("inventory:adjust"))])
async def adjust_product_inventory(
    product_id: UUID,
    payload: InventoryAdjustmentPayload,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    idem_key = (idempotency_key or payload.referenceCode or "").strip()
    if idem_key:
        await session.execute(
            text("DELETE FROM product_inventory_idempotency WHERE created_at < NOW() - INTERVAL '30 days'")
        )
        existing = (
            await session.execute(
                text("SELECT response_payload FROM product_inventory_idempotency WHERE idempotency_key = :key"),
                {"key": idem_key},
            )
        ).mappings().first()
        if existing:
            return dict(existing["response_payload"])
    if payload.delta is None and payload.quantity is None:
        raise HTTPException(status_code=400, detail="Provide either delta or quantity.")
    if payload.delta is not None and payload.quantity is not None:
        raise HTTPException(status_code=400, detail="Provide either delta or quantity, not both.")
    # Tự động phân giải variant_id nếu không được truyền lên
    actual_variant_id = payload.variantId
    if not actual_variant_id:
        active_variants = (
            await session.execute(
                text("SELECT id FROM product_variants WHERE product_id = :product_id AND deleted_at IS NULL"),
                {"product_id": product_id}
            )
        ).mappings().all()
        if len(active_variants) == 1:
            actual_variant_id = active_variants[0]["id"]
        elif len(active_variants) > 1:
            raise HTTPException(
                status_code=400,
                detail="Sản phẩm có nhiều biến thể. Vui lòng chọn biến thể cụ thể để điều chỉnh tồn kho."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Sản phẩm không có biến thể hoạt động nào."
            )

    row = (
        await session.execute(
            text(
                """
                SELECT id, stock_quantity, sku
                FROM product_variants
                WHERE id = :variant_id AND product_id = :product_id AND deleted_at IS NULL
                FOR UPDATE
                """
            ),
            {"variant_id": actual_variant_id, "product_id": product_id},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Variant not found.")
    
    old_quantity = int(row["stock_quantity"] or 0)
    new_quantity = payload.quantity if payload.quantity is not None else old_quantity + int(payload.delta or 0)
    if new_quantity < 0:
        raise HTTPException(status_code=400, detail="Inventory quantity cannot be negative.")
    await session.execute(
        text("UPDATE product_variants SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
        {"id": actual_variant_id, "quantity": new_quantity},
    )
    item_sku = row["sku"]

    # Calculate delta for IMEI mapping if delta not explicitly provided
    delta = int(payload.delta or 0) if payload.delta is not None else (new_quantity - old_quantity)

    imeis = [str(item).strip() for item in payload.imeis if str(item).strip()]
    if payload.transactionType == "RECEIPT" and delta > 0:
        if actual_variant_id and len(imeis) < delta:
            imeis.extend(generate_inventory_imei(item_sku, None) for _ in range(delta - len(imeis)))
        for imei in imeis[:delta]:
            await session.execute(
                text(
                    """
                    INSERT INTO product_imeis (
                        id, product_id, variant_id, imei, status, source_reference, received_at
                    )
                    VALUES (
                        :id, :product_id, :variant_id, :imei, 'IN_STOCK', :source_reference, NOW()
                    )
                    ON CONFLICT (imei) DO NOTHING
                    """
                ),
                {
                    "id": uuid4(),
                    "product_id": product_id,
                    "variant_id": actual_variant_id,
                    "imei": imei,
                    "source_reference": payload.referenceCode,
                },
            )
    await session.execute(
        text(
            """
            INSERT INTO inventory_adjustment_logs (
                id, product_id, variant_id, old_quantity, new_quantity, delta, transaction_type, reference_code, reason, note,
                supplier_name, unit_cost, location_code, location_name
            )
            VALUES (
                :id, :product_id, :variant_id, :old_quantity, :new_quantity, :delta, :transaction_type, :reference_code, :reason, :note,
                :supplier_name, :unit_cost, :location_code, :location_name
            )
            """
        ),
        {
            "id": uuid4(),
            "product_id": product_id,
            "variant_id": actual_variant_id,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "delta": delta,
            "transaction_type": payload.transactionType,
            "reference_code": payload.referenceCode,
            "reason": payload.reason,
            "note": payload.note,
            "supplier_name": payload.supplierName,
            "unit_cost": payload.unitCost,
            "location_code": payload.locationCode,
            "location_name": payload.locationName,
        },
    )
    response_payload = {"ok": True, "oldQuantity": old_quantity, "newQuantity": new_quantity}
    if idem_key:
        await session.execute(
            text(
                """
                INSERT INTO product_inventory_idempotency (idempotency_key, product_id, response_payload)
                VALUES (:key, :product_id, CAST(:response_payload AS jsonb))
                ON CONFLICT DO NOTHING
                """
            ),
            {"key": idem_key, "product_id": product_id, "response_payload": json.dumps(response_payload)},
        )
    await sync_parent_price_from_variants(session, product_id)
    await session.commit()
    return response_payload


@router.patch("/products/{product_id}/variants/{variant_id}/inventory", dependencies=[Depends(require_permission("inventory:adjust"))])
async def set_variant_inventory(product_id: UUID, variant_id: UUID, payload: VariantInventoryPayload, session: AsyncSession = Depends(get_session)) -> dict:
    return await adjust_product_inventory(
        product_id,
        InventoryAdjustmentPayload(
            variantId=variant_id,
            quantity=payload.quantity,
            transactionType=payload.transactionType,
            referenceCode=payload.referenceCode,
            reason=payload.reason,
            note=payload.note,
        ),
        idempotency_key=payload.referenceCode,
        session=session,
    )
