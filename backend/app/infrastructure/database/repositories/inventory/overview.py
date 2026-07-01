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
                    p.sales_config,
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
        {"product_id": product_id, "sales_config": json.dumps(sales_config, ensure_ascii=False)},
    )


async def list_inventory_snapshot_rows(session: AsyncSession, search: str) -> list[dict]:
    result = await session.execute(
        text(
            """
            WITH active_reservations AS (
                SELECT
                    product_id,
                    variant_id,
                    SUM(reserved_quantity)::int AS reserved_quantity
                FROM inventory_reservations
                WHERE status = 'ACTIVE'
                  AND (expires_at IS NULL OR expires_at > NOW())
                GROUP BY product_id, variant_id
            ),
            level_cost AS (
                SELECT
                    product_id,
                    variant_id,
                    MAX(average_unit_cost) AS average_unit_cost
                FROM inventory_levels
                GROUP BY product_id, variant_id
            ),
            level_locations AS (
                SELECT
                    il.product_id,
                    il.variant_id,
                    jsonb_agg(
                        jsonb_build_object(
                            'code', loc.code,
                            'name', loc.name,
                            'onHandQuantity', il.on_hand_quantity
                        )
                        ORDER BY loc.code
                    ) FILTER (WHERE il.on_hand_quantity <> 0) AS locations
                FROM inventory_levels il
                JOIN inventory_locations loc ON loc.id = il.location_id
                GROUP BY il.product_id, il.variant_id
            ),
            reserved_imeis AS (
                SELECT
                    product_id,
                    variant_id,
                    COUNT(*)::int AS reserved_quantity
                FROM product_imeis
                WHERE status = 'RESERVED'
                GROUP BY product_id, variant_id
            ),
            reserved_serials AS (
                SELECT
                    product_id,
                    variant_id,
                    COUNT(*)::int AS reserved_quantity
                FROM product_serial_numbers
                WHERE status = 'RESERVED'
                GROUP BY product_id, variant_id
            ),
            imei_summary AS (
                SELECT
                    product_id,
                    variant_id,
                    COUNT(*) FILTER (WHERE status = 'IN_STOCK')::int AS in_stock_imei_quantity,
                    COUNT(*) FILTER (WHERE status = 'RESERVED')::int AS reserved_imei_quantity,
                    COUNT(*) FILTER (WHERE status = 'SOLD')::int AS sold_imei_quantity,
                    COUNT(*) FILTER (WHERE status IN ('WARRANTY', 'IN_WARRANTY'))::int AS warranty_imei_quantity,
                    COUNT(*) FILTER (WHERE status IN ('RETIRED', 'SCRAP'))::int AS scrap_imei_quantity,
                    MAX(imei) FILTER (WHERE is_primary = TRUE) AS primary_imei,
                    COUNT(*) FILTER (WHERE is_primary = FALSE)::int AS supplemental_imei_quantity
                FROM product_imeis
                GROUP BY product_id, variant_id
            ),
            serial_summary AS (
                SELECT
                    product_id,
                    variant_id,
                    COUNT(*) FILTER (WHERE status = 'IN_STOCK')::int AS in_stock_serial_quantity,
                    COUNT(*) FILTER (WHERE status = 'RESERVED')::int AS reserved_serial_quantity,
                    COUNT(*) FILTER (WHERE status = 'SOLD')::int AS sold_serial_quantity,
                    COUNT(*) FILTER (WHERE status IN ('WARRANTY', 'IN_WARRANTY'))::int AS warranty_serial_quantity,
                    COUNT(*) FILTER (WHERE status IN ('RETIRED', 'SCRAP'))::int AS scrap_serial_quantity
                FROM product_serial_numbers
                GROUP BY product_id, variant_id
            )
            SELECT
                p.id::text AS "productId",
                p.name AS "productName",
                p.sku AS "productSku",
                p.price AS "productPrice",
                p.sale_price AS "productSalePrice",
                p.stock_quantity AS "productStock",
                p.status AS "productStatus",
                p.category_id::text AS "categoryId",
                p.subcategory_id::text AS "subcategoryId",
                p.brand_id::text AS "brandId",
                p.sales_config AS "salesConfig",
                child.inventory_policy AS "childInventoryPolicy",
                parent.inventory_policy AS "parentInventoryPolicy",
                pv.id::text AS "variantId",
                pv.sku AS "variantSku",
                pv.price AS "variantPrice",
                pv.sale_price AS "variantSalePrice",
                pv.configuration,
                pv.color_name AS "colorName",
                pv.stock_quantity AS "variantStock",
                COALESCE(NULLIF(pv.sale_price, 0), NULLIF(pv.price, 0), NULLIF(p.sale_price, 0), p.price, 0) AS "displayPrice",
                COALESCE(vr.reserved_quantity, pr.reserved_quantity, 0) AS "reservationReservedQuantity",
                COALESCE(vi.reserved_quantity, pi.reserved_quantity, 0) AS "imeiReservedQuantity",
                COALESCE(vsnr.reserved_quantity, psnr.reserved_quantity, 0) AS "serialReservedQuantity",
                COALESCE(vlc.average_unit_cost, plc.average_unit_cost, 0) AS "averageUnitCost",
                COALESCE(vll.locations, pll.locations, '[]'::jsonb) AS locations,
                COALESCE(vs.in_stock_imei_quantity, ps.in_stock_imei_quantity, 0) AS "inStockImeiQuantity",
                COALESCE(vs.reserved_imei_quantity, ps.reserved_imei_quantity, 0) AS "reservedImeiQuantity",
                COALESCE(vs.sold_imei_quantity, ps.sold_imei_quantity, 0) AS "soldImeiQuantity",
                COALESCE(vs.warranty_imei_quantity, ps.warranty_imei_quantity, 0) AS "warrantyImeiQuantity",
                COALESCE(vs.scrap_imei_quantity, ps.scrap_imei_quantity, 0) AS "scrapImeiQuantity",
                COALESCE(vs.primary_imei, ps.primary_imei) AS "primaryImei",
                COALESCE(vs.supplemental_imei_quantity, ps.supplemental_imei_quantity, 0) AS "supplementalImeiQuantity",
                COALESCE(vss.in_stock_serial_quantity, pss.in_stock_serial_quantity, 0) AS "inStockSerialQuantity",
                COALESCE(vss.reserved_serial_quantity, pss.reserved_serial_quantity, 0) AS "reservedSerialQuantity",
                COALESCE(vss.sold_serial_quantity, pss.sold_serial_quantity, 0) AS "soldSerialQuantity",
                COALESCE(vss.warranty_serial_quantity, pss.warranty_serial_quantity, 0) AS "warrantySerialQuantity",
                COALESCE(vss.scrap_serial_quantity, pss.scrap_serial_quantity, 0) AS "scrapSerialQuantity"
            FROM products p
            LEFT JOIN product_variants pv ON pv.product_id = p.id AND pv.deleted_at IS NULL
            LEFT JOIN categories child ON child.id = p.subcategory_id
            LEFT JOIN categories parent ON parent.id = COALESCE(p.category_id, child.parent_id)
            LEFT JOIN active_reservations vr ON vr.variant_id = pv.id
            LEFT JOIN active_reservations pr ON pr.product_id = p.id AND pr.variant_id IS NULL
            LEFT JOIN level_cost vlc ON vlc.variant_id = pv.id
            LEFT JOIN level_cost plc ON plc.product_id = p.id AND plc.variant_id IS NULL
            LEFT JOIN level_locations vll ON vll.variant_id = pv.id
            LEFT JOIN level_locations pll ON pll.product_id = p.id AND pll.variant_id IS NULL
            LEFT JOIN reserved_imeis vi ON vi.variant_id = pv.id
            LEFT JOIN reserved_imeis pi ON pi.product_id = p.id AND pi.variant_id IS NULL
            LEFT JOIN reserved_serials vsnr ON vsnr.variant_id = pv.id
            LEFT JOIN reserved_serials psnr ON psnr.product_id = p.id AND psnr.variant_id IS NULL
            LEFT JOIN imei_summary vs ON vs.variant_id = pv.id
            LEFT JOIN imei_summary ps ON ps.product_id = p.id AND ps.variant_id IS NULL
            LEFT JOIN serial_summary vss ON vss.variant_id = pv.id
            LEFT JOIN serial_summary pss ON pss.product_id = p.id AND pss.variant_id IS NULL
            WHERE p.deleted_at IS NULL
              AND p.status <> 'MERGED'
              AND (
                :search = ''
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(p.sku) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
              )
            ORDER BY p.created_at DESC, pv.created_at, pv.sku
            """
        ),
        {"search": search, "pattern": f"%{search}%"},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_level_rows(session: AsyncSession, search: str) -> list[dict]:
    return await list_inventory_snapshot_rows(session, search)


async def list_inventory_aging_rows(session: AsyncSession, search: str = "", bucket: str = "") -> list[dict]:
    result = await session.execute(
        text(
            """
            WITH lot_rows AS (
                SELECT
                    lot.id,
                    lot.product_id,
                    lot.variant_id,
                    lot.location_id,
                    lot.remaining_quantity,
                    COALESCE(lot.unit_cost, 0) AS unit_cost,
                    lot.received_at,
                    GREATEST(FLOOR(EXTRACT(EPOCH FROM (NOW() - lot.received_at)) / 86400), 0)::int AS age_days
                FROM inventory_lots lot
                WHERE lot.status = 'ACTIVE'
                  AND lot.remaining_quantity > 0
            ),
            shaped AS (
                SELECT
                    CASE
                        WHEN age_days <= 30 THEN '0_30'
                        WHEN age_days <= 90 THEN '31_90'
                        WHEN age_days <= 180 THEN '91_180'
                        ELSE '180_PLUS'
                    END AS bucket,
                    lot_rows.product_id,
                    lot_rows.variant_id,
                    lot_rows.location_id,
                    lot_rows.remaining_quantity,
                    lot_rows.unit_cost,
                    lot_rows.received_at,
                    lot_rows.age_days
                FROM lot_rows
            )
            SELECT
                shaped.bucket,
                p.id::text AS "productId",
                p.name AS "productName",
                p.sku AS "productSku",
                pv.id::text AS "variantId",
                pv.sku AS "variantSku",
                pv.color_name AS "variantColor",
                pv.configuration AS "variantConfiguration",
                loc.id::text AS "locationId",
                loc.code AS "locationCode",
                loc.name AS "locationName",
                SUM(shaped.remaining_quantity)::int AS quantity,
                SUM(shaped.remaining_quantity * shaped.unit_cost) AS "totalCost",
                MIN(shaped.received_at) AS "oldestReceivedAt",
                MAX(shaped.received_at) AS "newestReceivedAt",
                MAX(shaped.age_days)::int AS "maxAgeDays",
                ROUND(AVG(shaped.age_days)::numeric, 1) AS "averageAgeDays"
            FROM shaped
            LEFT JOIN product_variants pv ON pv.id = shaped.variant_id
            JOIN products p ON p.id = COALESCE(shaped.product_id, pv.product_id)
            JOIN inventory_locations loc ON loc.id = shaped.location_id
            WHERE p.deleted_at IS NULL
              AND p.status <> 'MERGED'
              AND (:bucket = '' OR shaped.bucket = :bucket)
              AND (
                :search = ''
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(p.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(loc.code, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(loc.name, '')) LIKE LOWER(:pattern)
              )
            GROUP BY
                shaped.bucket,
                p.id,
                p.name,
                p.sku,
                pv.id,
                pv.sku,
                pv.color_name,
                pv.configuration,
                loc.id,
                loc.code,
                loc.name
            ORDER BY
                MAX(shaped.age_days) DESC,
                SUM(shaped.remaining_quantity * shaped.unit_cost) DESC,
                p.name ASC,
                pv.sku ASC,
                loc.code ASC
            """
        ),
        {"search": search, "pattern": f"%{search}%", "bucket": bucket},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_ledger_rows(
    session: AsyncSession,
    *,
    search: str = "",
    product_id: str = "",
    date_from: str = "",
    date_to: str = "",
    transaction_type: str = "",
    reason: str = "",
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                ial.id::text AS id,
                ial.created_at AS "createdAt",
                ial.product_id::text AS "productId",
                ial.variant_id::text AS "variantId",
                p.name AS "productName",
                p.sku AS "productSku",
                pv.sku AS "variantSku",
                pv.color_name AS "variantColor",
                pv.configuration AS "variantConfiguration",
                ial.old_quantity AS "oldQuantity",
                ial.new_quantity AS "newQuantity",
                ial.delta,
                ial.transaction_type AS "transactionType",
                ial.reference_code AS "referenceCode",
                ial.reason,
                ial.note,
                ial.supplier_name AS "supplierName",
                ial.unit_cost AS "unitCost",
                ial.location_code AS "locationCode",
                ial.location_name AS "locationName"
            FROM inventory_adjustment_logs ial
            JOIN products p ON p.id = ial.product_id
            LEFT JOIN product_variants pv ON pv.id = ial.variant_id
            WHERE p.deleted_at IS NULL
              AND p.status <> 'MERGED'
              AND (:product_id = '' OR ial.product_id::text = :product_id OR ial.variant_id::text = :product_id)
              AND (:transaction_type = '' OR ial.transaction_type = :transaction_type)
              AND (:reason = '' OR ial.reason = :reason)
              AND (:date_from = '' OR ial.created_at >= CAST(NULLIF(:date_from, '') AS date))
              AND (:date_to = '' OR ial.created_at < CAST(NULLIF(:date_to, '') AS date) + INTERVAL '1 day')
              AND (
                :search = ''
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(p.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(ial.reference_code, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(ial.reason, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(ial.location_code, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(ial.location_name, '')) LIKE LOWER(:pattern)
              )
            ORDER BY ial.created_at DESC, ial.id DESC
            """
        ),
        {
            "search": search,
            "pattern": f"%{search}%",
            "product_id": product_id,
            "date_from": date_from,
            "date_to": date_to,
            "transaction_type": transaction_type,
            "reason": reason,
        },
    )
    return [dict(row) for row in result.mappings().all()]
