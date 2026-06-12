import json
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_product_inventory_summary(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
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
    return dict(row) if row else None


async def list_product_inventory_variants(session: AsyncSession, product_id: UUID) -> list[dict]:
    result = await session.execute(
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
    return [dict(row) for row in result.mappings().all()]


async def get_product_inventory_policy(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    p.id,
                    p.name,
                    p.sku,
                    p.category_id,
                    p.subcategory_id,
                    child.inventory_policy AS child_policy,
                    parent.inventory_policy AS parent_policy
                FROM products p
                LEFT JOIN categories child ON child.id = p.subcategory_id
                LEFT JOIN categories parent ON parent.id = COALESCE(p.category_id, child.parent_id)
                WHERE p.id = :product_id
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def list_inventory_adjustment_logs(session: AsyncSession, product_id: UUID) -> list[dict]:
    result = await session.execute(
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
    return [dict(row) for row in result.mappings().all()]


async def get_product_sales_config_for_update(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text("SELECT sales_config FROM products WHERE id = :product_id FOR UPDATE"),
            {"product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_product_sales_config(session: AsyncSession, *, product_id: UUID, sales_config: dict) -> None:
    await session.execute(
        text("UPDATE products SET sales_config = CAST(:sales_config AS jsonb), updated_at = NOW() WHERE id = :product_id"),
        {"product_id": product_id, "sales_config": json.dumps(sales_config)},
    )


async def list_inventory_snapshot_rows(session: AsyncSession, search: str) -> list[dict]:
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
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_receipts(session: AsyncSession, search: str = "") -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                ial.reference_code AS "referenceCode",
                MIN(ial.created_at) AS "createdAt",
                MAX(ial.supplier_name) AS "supplierName",
                MAX(ial.location_code) AS "locationCode",
                MAX(ial.location_name) AS "locationName",
                COUNT(*)::int AS "lineCount",
                SUM(GREATEST(ial.delta, 0))::int AS "totalQuantity",
                SUM(COALESCE(ial.unit_cost, 0) * GREATEST(ial.delta, 0)) AS "totalCost",
                jsonb_agg(
                    jsonb_build_object(
                        'id', ial.id::text,
                        'productId', ial.product_id::text,
                        'variantId', ial.variant_id::text,
                        'productName', p.name,
                        'productSku', p.sku,
                        'variantSku', pv.sku,
                        'variantColor', pv.color_name,
                        'variantConfiguration', pv.configuration,
                        'quantity', ial.delta,
                        'unitCost', ial.unit_cost,
                        'note', ial.note,
                        'createdAt', ial.created_at
                    )
                    ORDER BY ial.created_at, p.name, pv.sku
                ) AS lines
            FROM inventory_adjustment_logs ial
            JOIN products p ON p.id = ial.product_id
            LEFT JOIN product_variants pv ON pv.id = ial.variant_id
            WHERE ial.transaction_type = 'RECEIPT'
              AND (:search = ''
                OR LOWER(COALESCE(ial.reference_code, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(ial.supplier_name, '')) LIKE LOWER(:pattern)
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(p.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
              )
            GROUP BY ial.reference_code
            ORDER BY MIN(ial.created_at) DESC
            LIMIT 200
            """
        ),
        {"search": search, "pattern": f"%{search}%"},
    )
    return [dict(row) for row in result.mappings().all()]


async def delete_old_inventory_idempotency(session: AsyncSession) -> None:
    await session.execute(text("DELETE FROM product_inventory_idempotency WHERE created_at < NOW() - INTERVAL '30 days'"))


async def get_inventory_idempotency_response(session: AsyncSession, key: str) -> dict | None:
    row = (
        await session.execute(
            text("SELECT response_payload FROM product_inventory_idempotency WHERE idempotency_key = :key"),
            {"key": key},
        )
    ).mappings().first()
    return dict(row["response_payload"]) if row else None


async def list_product_variant_ids(session: AsyncSession, product_id: UUID) -> list[dict]:
    rows = (
        await session.execute(
            text("SELECT id FROM product_variants WHERE product_id = :product_id AND deleted_at IS NULL"),
            {"product_id": product_id},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def get_variant_inventory_for_update(session: AsyncSession, *, product_id: UUID, variant_id: UUID) -> dict | None:
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
            {"variant_id": variant_id, "product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def list_existing_imeis(session: AsyncSession, imeis: list[str]) -> list[str]:
    if not imeis:
        return []
    rows = (
        await session.execute(
            text("SELECT imei FROM product_imeis WHERE imei = ANY(:imeis)"),
            {"imeis": imeis},
        )
    ).mappings().all()
    return [str(row["imei"]) for row in rows]


async def update_variant_stock(session: AsyncSession, *, variant_id: UUID, quantity: int) -> None:
    await session.execute(
        text("UPDATE product_variants SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
        {"id": variant_id, "quantity": quantity},
    )


async def insert_product_imei(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID,
    imei: str,
    source_reference: str,
) -> None:
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
            "variant_id": variant_id,
            "imei": imei,
            "source_reference": source_reference,
        },
    )


async def insert_inventory_adjustment_log(
    session: AsyncSession,
    *,
    log_id: UUID,
    product_id: UUID,
    variant_id: UUID,
    old_quantity: int,
    new_quantity: int,
    delta: int,
    transaction_type: str,
    reference_code: str,
    reason: str,
    note: str | None,
    supplier_name: str | None,
    unit_cost: float | None,
    location_code: str | None,
    location_name: str | None,
) -> None:
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
            "id": log_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "delta": delta,
            "transaction_type": transaction_type,
            "reference_code": reference_code,
            "reason": reason,
            "note": note,
            "supplier_name": supplier_name,
            "unit_cost": unit_cost,
            "location_code": location_code,
            "location_name": location_name,
        },
    )


async def insert_inventory_idempotency_response(session: AsyncSession, *, key: str, product_id: UUID, response_payload: dict) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_inventory_idempotency (idempotency_key, product_id, response_payload)
            VALUES (:key, :product_id, CAST(:response_payload AS jsonb))
            ON CONFLICT DO NOTHING
            """
        ),
        {"key": key, "product_id": product_id, "response_payload": json.dumps(response_payload)},
    )
