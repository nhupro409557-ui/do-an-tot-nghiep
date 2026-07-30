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
            level_reservations AS (
                SELECT
                    product_id,
                    variant_id,
                    SUM(reserved_quantity)::int AS reserved_quantity
                FROM inventory_levels
                WHERE reserved_quantity > 0
                GROUP BY product_id, variant_id
            ),
            level_stock AS (
                SELECT
                    il.product_id,
                    il.variant_id,
                    SUM(il.on_hand_quantity)::int AS physical_stock,
                    SUM(il.on_hand_quantity) FILTER (
                        WHERE loc.status = 'ACTIVE' AND loc.purpose IN ('STORAGE', 'VIRTUAL')
                    )::int AS sellable_stock
                FROM inventory_levels il
                JOIN inventory_locations loc ON loc.id = il.location_id
                GROUP BY il.product_id, il.variant_id
            ),
            level_cost AS (
                SELECT
                    product_id,
                    variant_id,
                    CASE
                        WHEN SUM(on_hand_quantity) > 0 THEN ROUND(
                            SUM(on_hand_quantity * average_unit_cost) / SUM(on_hand_quantity),
                            2
                        )
                        ELSE 0
                    END AS average_unit_cost
                FROM inventory_levels
                GROUP BY product_id, variant_id
            ),
            location_imeis AS (
                SELECT
                    product_id,
                    variant_id,
                    location_id,
                    jsonb_agg(
                        jsonb_build_object(
                            'id', id::text,
                            'code', imei,
                            'status', status,
                            'isPrimary', is_primary
                        )
                        ORDER BY is_primary DESC, imei
                    ) AS imeis
                FROM product_imeis
                WHERE location_id IS NOT NULL
                  AND status IN ('IN_STOCK', 'RESERVED')
                GROUP BY product_id, variant_id, location_id
            ),
            location_serials AS (
                SELECT
                    product_id,
                    variant_id,
                    location_id,
                    jsonb_agg(
                        jsonb_build_object(
                            'id', id::text,
                            'code', serial_number,
                            'status', status
                        )
                        ORDER BY serial_number
                    ) AS serial_numbers
                FROM product_serial_numbers
                WHERE location_id IS NOT NULL
                  AND status IN ('IN_STOCK', 'RESERVED')
                GROUP BY product_id, variant_id, location_id
            ),
            location_identifier_units AS (
                SELECT
                    pair.product_id,
                    pair.variant_id,
                    imei1.location_id,
                    jsonb_agg(
                        jsonb_build_object(
                            'pairId', pair.id::text,
                            'imei1', pair.imei1,
                            'imei2', pair.imei2,
                            'serialNumber', pair.serial_number,
                            'status', imei1.status,
                            'isPrimary', imei1.is_primary,
                            'isConsistent', (
                                serial.location_id IS NOT DISTINCT FROM imei1.location_id
                                AND serial.status = imei1.status
                                AND (imei2.id IS NULL OR (
                                    imei2.location_id IS NOT DISTINCT FROM imei1.location_id
                                    AND imei2.status = imei1.status
                                ))
                            )
                        )
                        ORDER BY imei1.is_primary DESC, pair.imei1
                    ) AS identifier_units
                FROM product_identifier_pairs pair
                JOIN product_imeis imei1
                  ON imei1.product_id = pair.product_id AND imei1.imei = pair.imei1
                LEFT JOIN product_imeis imei2
                  ON imei2.product_id = pair.product_id AND imei2.imei = pair.imei2
                JOIN product_serial_numbers serial
                  ON serial.product_id = pair.product_id AND serial.serial_number = pair.serial_number
                WHERE imei1.location_id IS NOT NULL
                  AND imei1.status IN ('IN_STOCK', 'RESERVED')
                GROUP BY pair.product_id, pair.variant_id, imei1.location_id
            ),
            level_locations AS (
                SELECT
                    il.product_id,
                    il.variant_id,
                    jsonb_agg(
                        jsonb_build_object(
                            'id', loc.id::text,
                            'code', loc.code,
                            'name', loc.name,
                            'zone', loc.zone,
                            'onHandQuantity', il.on_hand_quantity,
                            'reservedQuantity', il.reserved_quantity,
                            'availableQuantity', GREATEST(il.on_hand_quantity - il.reserved_quantity, 0),
                            'imeis', COALESCE(li.imeis, '[]'::jsonb),
                            'serialNumbers', COALESCE(ls.serial_numbers, '[]'::jsonb),
                            'identifierUnits', COALESCE(lu.identifier_units, '[]'::jsonb)
                        )
                        ORDER BY loc.code
                    ) FILTER (WHERE il.on_hand_quantity <> 0) AS locations
                FROM inventory_levels il
                JOIN inventory_locations loc ON loc.id = il.location_id
                LEFT JOIN location_imeis li
                  ON li.location_id = il.location_id
                 AND (
                    (il.variant_id IS NOT NULL AND li.variant_id = il.variant_id)
                    OR (il.variant_id IS NULL AND li.variant_id IS NULL AND li.product_id = il.product_id)
                 )
                LEFT JOIN location_serials ls
                  ON ls.location_id = il.location_id
                 AND (
                    (il.variant_id IS NOT NULL AND ls.variant_id = il.variant_id)
                    OR (il.variant_id IS NULL AND ls.variant_id IS NULL AND ls.product_id = il.product_id)
                 )
                LEFT JOIN location_identifier_units lu
                  ON lu.location_id = il.location_id
                 AND (
                    (il.variant_id IS NOT NULL AND lu.variant_id = il.variant_id)
                    OR (il.variant_id IS NULL AND lu.variant_id IS NULL AND lu.product_id = il.product_id)
                 )
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
                COALESCE(vls.physical_stock, pls.physical_stock) AS "levelPhysicalStock",
                COALESCE(vls.sellable_stock, pls.sellable_stock, 0) AS "levelSellableStock",
                COALESCE(NULLIF(pv.sale_price, 0), NULLIF(pv.price, 0), NULLIF(p.sale_price, 0), p.price, 0) AS "displayPrice",
                GREATEST(
                    COALESCE(vr.reserved_quantity, pr.reserved_quantity, 0),
                    COALESCE(vlr.reserved_quantity, plr.reserved_quantity, 0)
                ) AS "reservationReservedQuantity",
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
            LEFT JOIN level_reservations vlr ON vlr.variant_id = pv.id
            LEFT JOIN level_reservations plr ON plr.product_id = p.id AND plr.variant_id IS NULL
            LEFT JOIN level_stock vls ON vls.variant_id = pv.id
            LEFT JOIN level_stock pls ON pls.product_id = p.id AND pls.variant_id IS NULL
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


async def list_inventory_reconciliation_rows(
    session: AsyncSession,
    search: str = "",
    issue_type: str = "",
) -> list[dict]:
    result = await session.execute(
        text(
            """
            WITH level_rows AS (
                SELECT
                    il.product_id,
                    il.variant_id,
                    il.location_id,
                    il.on_hand_quantity,
                    il.reserved_quantity,
                    p.id AS resolved_product_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    pv.sku AS variant_sku,
                    pv.color_name AS variant_color,
                    pv.configuration AS variant_configuration,
                    loc.code AS location_code,
                    loc.name AS location_name
                FROM inventory_levels il
                LEFT JOIN product_variants pv ON pv.id = il.variant_id
                JOIN products p ON p.id = COALESCE(il.product_id, pv.product_id)
                JOIN inventory_locations loc ON loc.id = il.location_id
                WHERE il.on_hand_quantity > 0
                  AND p.deleted_at IS NULL
                  AND p.status <> 'MERGED'
            ),
            imei_counts AS (
                SELECT
                    pi.product_id,
                    pi.variant_id,
                    pi.location_id,
                    COUNT(*) FILTER (WHERE pi.is_primary = TRUE)::int AS primary_quantity,
                    COUNT(*)::int AS total_quantity
                FROM product_imeis pi
                WHERE pi.status = 'IN_STOCK'
                  AND pi.location_id IS NOT NULL
                GROUP BY pi.product_id, pi.variant_id, pi.location_id
            ),
            serial_counts AS (
                SELECT
                    psn.product_id,
                    psn.variant_id,
                    psn.location_id,
                    COUNT(*)::int AS total_quantity
                FROM product_serial_numbers psn
                WHERE psn.status = 'IN_STOCK'
                  AND psn.location_id IS NOT NULL
                GROUP BY psn.product_id, psn.variant_id, psn.location_id
            ),
            level_mismatches AS (
                SELECT
                    'LEVEL_GT_IDENTIFIERS'::text AS issue_type,
                    NULL::text AS identifier_type,
                    lr.resolved_product_id::text AS product_id,
                    lr.variant_id::text AS variant_id,
                    lr.product_name,
                    lr.product_sku,
                    lr.variant_sku,
                    lr.variant_color,
                    lr.variant_configuration,
                    lr.location_id::text AS location_id,
                    lr.location_code,
                    lr.location_name,
                    lr.on_hand_quantity::int AS on_hand_quantity,
                    GREATEST(
                        CASE WHEN COALESCE(ic.primary_quantity, 0) > 0 THEN ic.primary_quantity ELSE COALESCE(ic.total_quantity, 0) END,
                        COALESCE(sc.total_quantity, 0)
                    )::int AS identifier_quantity,
                    (
                        lr.on_hand_quantity - GREATEST(
                            CASE WHEN COALESCE(ic.primary_quantity, 0) > 0 THEN ic.primary_quantity ELSE COALESCE(ic.total_quantity, 0) END,
                            COALESCE(sc.total_quantity, 0)
                        )
                    )::int AS difference_quantity,
                    NULL::text AS identifier_value,
                    NULL::text AS identifier_status,
                    'Tồn trên kệ lớn hơn số mã IN_STOCK đang gắn vào kệ.'::text AS message,
                    lr.product_name || ' ' || COALESCE(lr.product_sku, '') || ' ' || COALESCE(lr.variant_sku, '') || ' ' || lr.location_code AS searchable_text
                FROM level_rows lr
                LEFT JOIN imei_counts ic
                  ON ic.location_id = lr.location_id
                 AND (
                    (lr.variant_id IS NOT NULL AND ic.variant_id = lr.variant_id)
                    OR (lr.variant_id IS NULL AND ic.variant_id IS NULL AND ic.product_id = lr.resolved_product_id)
                 )
                LEFT JOIN serial_counts sc
                  ON sc.location_id = lr.location_id
                 AND (
                    (lr.variant_id IS NOT NULL AND sc.variant_id = lr.variant_id)
                    OR (lr.variant_id IS NULL AND sc.variant_id IS NULL AND sc.product_id = lr.resolved_product_id)
                 )
                WHERE GREATEST(COALESCE(ic.total_quantity, 0), COALESCE(sc.total_quantity, 0)) > 0
                  AND lr.on_hand_quantity > GREATEST(
                    CASE WHEN COALESCE(ic.primary_quantity, 0) > 0 THEN ic.primary_quantity ELSE COALESCE(ic.total_quantity, 0) END,
                    COALESCE(sc.total_quantity, 0)
                  )
            ),
            imei_without_location AS (
                SELECT
                    'IDENTIFIER_IN_STOCK_WITHOUT_LOCATION'::text AS issue_type,
                    'IMEI'::text AS identifier_type,
                    p.id::text AS product_id,
                    pi.variant_id::text AS variant_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    pv.sku AS variant_sku,
                    pv.color_name AS variant_color,
                    pv.configuration AS variant_configuration,
                    NULL::text AS location_id,
                    NULL::text AS location_code,
                    NULL::text AS location_name,
                    NULL::int AS on_hand_quantity,
                    NULL::int AS identifier_quantity,
                    NULL::int AS difference_quantity,
                    pi.imei AS identifier_value,
                    pi.status AS identifier_status,
                    'IMEI đang IN_STOCK nhưng chưa có kệ.'::text AS message,
                    p.name || ' ' || COALESCE(p.sku, '') || ' ' || COALESCE(pv.sku, '') || ' ' || pi.imei AS searchable_text
                FROM product_imeis pi
                LEFT JOIN product_variants pv ON pv.id = pi.variant_id
                JOIN products p ON p.id = COALESCE(pi.product_id, pv.product_id)
                WHERE pi.status = 'IN_STOCK'
                  AND pi.location_id IS NULL
                  AND p.deleted_at IS NULL
                  AND p.status <> 'MERGED'
            ),
            serial_without_location AS (
                SELECT
                    'IDENTIFIER_IN_STOCK_WITHOUT_LOCATION'::text AS issue_type,
                    'SERIAL'::text AS identifier_type,
                    p.id::text AS product_id,
                    psn.variant_id::text AS variant_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    pv.sku AS variant_sku,
                    pv.color_name AS variant_color,
                    pv.configuration AS variant_configuration,
                    NULL::text AS location_id,
                    NULL::text AS location_code,
                    NULL::text AS location_name,
                    NULL::int AS on_hand_quantity,
                    NULL::int AS identifier_quantity,
                    NULL::int AS difference_quantity,
                    psn.serial_number AS identifier_value,
                    psn.status AS identifier_status,
                    'Serial đang IN_STOCK nhưng chưa có kệ.'::text AS message,
                    p.name || ' ' || COALESCE(p.sku, '') || ' ' || COALESCE(pv.sku, '') || ' ' || psn.serial_number AS searchable_text
                FROM product_serial_numbers psn
                LEFT JOIN product_variants pv ON pv.id = psn.variant_id
                JOIN products p ON p.id = COALESCE(psn.product_id, pv.product_id)
                WHERE psn.status = 'IN_STOCK'
                  AND psn.location_id IS NULL
                  AND p.deleted_at IS NULL
                  AND p.status <> 'MERGED'
            ),
            imei_without_level AS (
                SELECT
                    'IDENTIFIER_LOCATION_WITHOUT_LEVEL'::text AS issue_type,
                    'IMEI'::text AS identifier_type,
                    p.id::text AS product_id,
                    pi.variant_id::text AS variant_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    pv.sku AS variant_sku,
                    pv.color_name AS variant_color,
                    pv.configuration AS variant_configuration,
                    loc.id::text AS location_id,
                    loc.code AS location_code,
                    loc.name AS location_name,
                    COALESCE(il.on_hand_quantity, 0)::int AS on_hand_quantity,
                    1::int AS identifier_quantity,
                    NULL::int AS difference_quantity,
                    pi.imei AS identifier_value,
                    pi.status AS identifier_status,
                    'IMEI có kệ nhưng inventory_levels tại kệ này không có tồn.'::text AS message,
                    p.name || ' ' || COALESCE(p.sku, '') || ' ' || COALESCE(pv.sku, '') || ' ' || pi.imei || ' ' || loc.code AS searchable_text
                FROM product_imeis pi
                LEFT JOIN product_variants pv ON pv.id = pi.variant_id
                JOIN products p ON p.id = COALESCE(pi.product_id, pv.product_id)
                JOIN inventory_locations loc ON loc.id = pi.location_id
                LEFT JOIN inventory_levels il
                  ON il.location_id = pi.location_id
                 AND (
                    (pi.variant_id IS NOT NULL AND il.variant_id = pi.variant_id)
                    OR (pi.variant_id IS NULL AND il.variant_id IS NULL AND il.product_id = p.id)
                 )
                WHERE pi.status = 'IN_STOCK'
                  AND pi.location_id IS NOT NULL
                  AND COALESCE(il.on_hand_quantity, 0) <= 0
                  AND p.deleted_at IS NULL
                  AND p.status <> 'MERGED'
            ),
            serial_without_level AS (
                SELECT
                    'IDENTIFIER_LOCATION_WITHOUT_LEVEL'::text AS issue_type,
                    'SERIAL'::text AS identifier_type,
                    p.id::text AS product_id,
                    psn.variant_id::text AS variant_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    pv.sku AS variant_sku,
                    pv.color_name AS variant_color,
                    pv.configuration AS variant_configuration,
                    loc.id::text AS location_id,
                    loc.code AS location_code,
                    loc.name AS location_name,
                    COALESCE(il.on_hand_quantity, 0)::int AS on_hand_quantity,
                    1::int AS identifier_quantity,
                    NULL::int AS difference_quantity,
                    psn.serial_number AS identifier_value,
                    psn.status AS identifier_status,
                    'Serial có kệ nhưng inventory_levels tại kệ này không có tồn.'::text AS message,
                    p.name || ' ' || COALESCE(p.sku, '') || ' ' || COALESCE(pv.sku, '') || ' ' || psn.serial_number || ' ' || loc.code AS searchable_text
                FROM product_serial_numbers psn
                LEFT JOIN product_variants pv ON pv.id = psn.variant_id
                JOIN products p ON p.id = COALESCE(psn.product_id, pv.product_id)
                JOIN inventory_locations loc ON loc.id = psn.location_id
                LEFT JOIN inventory_levels il
                  ON il.location_id = psn.location_id
                 AND (
                    (psn.variant_id IS NOT NULL AND il.variant_id = psn.variant_id)
                    OR (psn.variant_id IS NULL AND il.variant_id IS NULL AND il.product_id = p.id)
                 )
                WHERE psn.status = 'IN_STOCK'
                  AND psn.location_id IS NOT NULL
                  AND COALESCE(il.on_hand_quantity, 0) <= 0
                  AND p.deleted_at IS NULL
                  AND p.status <> 'MERGED'
            ),
            imei_terminal_with_location AS (
                SELECT
                    'TERMINAL_IDENTIFIER_WITH_LOCATION'::text AS issue_type,
                    'IMEI'::text AS identifier_type,
                    p.id::text AS product_id,
                    pi.variant_id::text AS variant_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    pv.sku AS variant_sku,
                    pv.color_name AS variant_color,
                    pv.configuration AS variant_configuration,
                    loc.id::text AS location_id,
                    loc.code AS location_code,
                    loc.name AS location_name,
                    NULL::int AS on_hand_quantity,
                    NULL::int AS identifier_quantity,
                    NULL::int AS difference_quantity,
                    pi.imei AS identifier_value,
                    pi.status AS identifier_status,
                    'IMEI đã rời kho hoặc kết thúc vòng đời nhưng vẫn còn gắn kệ.'::text AS message,
                    p.name || ' ' || COALESCE(p.sku, '') || ' ' || COALESCE(pv.sku, '') || ' ' || pi.imei || ' ' || loc.code || ' ' || pi.status AS searchable_text
                FROM product_imeis pi
                LEFT JOIN product_variants pv ON pv.id = pi.variant_id
                JOIN products p ON p.id = COALESCE(pi.product_id, pv.product_id)
                JOIN inventory_locations loc ON loc.id = pi.location_id
                WHERE pi.status IN ('SOLD', 'SCRAP', 'LIQUIDATED', 'OUT_OF_SYSTEM', 'RTV_COMPLETED', 'RETIRED', 'REVERSED')
                  AND pi.location_id IS NOT NULL
                  AND p.deleted_at IS NULL
                  AND p.status <> 'MERGED'
            ),
            serial_terminal_with_location AS (
                SELECT
                    'TERMINAL_IDENTIFIER_WITH_LOCATION'::text AS issue_type,
                    'SERIAL'::text AS identifier_type,
                    p.id::text AS product_id,
                    psn.variant_id::text AS variant_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    pv.sku AS variant_sku,
                    pv.color_name AS variant_color,
                    pv.configuration AS variant_configuration,
                    loc.id::text AS location_id,
                    loc.code AS location_code,
                    loc.name AS location_name,
                    NULL::int AS on_hand_quantity,
                    NULL::int AS identifier_quantity,
                    NULL::int AS difference_quantity,
                    psn.serial_number AS identifier_value,
                    psn.status AS identifier_status,
                    'Serial đã rời kho hoặc kết thúc vòng đời nhưng vẫn còn gắn kệ.'::text AS message,
                    p.name || ' ' || COALESCE(p.sku, '') || ' ' || COALESCE(pv.sku, '') || ' ' || psn.serial_number || ' ' || loc.code || ' ' || psn.status AS searchable_text
                FROM product_serial_numbers psn
                LEFT JOIN product_variants pv ON pv.id = psn.variant_id
                JOIN products p ON p.id = COALESCE(psn.product_id, pv.product_id)
                JOIN inventory_locations loc ON loc.id = psn.location_id
                WHERE psn.status IN ('SOLD', 'SCRAP', 'LIQUIDATED', 'OUT_OF_SYSTEM', 'RTV_COMPLETED', 'RETIRED', 'REVERSED')
                  AND psn.location_id IS NOT NULL
                  AND p.deleted_at IS NULL
                  AND p.status <> 'MERGED'
            ),
            sellable_stock_mismatch AS (
                SELECT
                    'SELLABLE_STOCK_MISMATCH'::text AS issue_type,
                    NULL::text AS identifier_type,
                    p.id::text AS product_id,
                    pv.id::text AS variant_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    pv.sku AS variant_sku,
                    pv.color_name AS variant_color,
                    pv.configuration AS variant_configuration,
                    NULL::text AS location_id,
                    NULL::text AS location_code,
                    NULL::text AS location_name,
                    COALESCE(pv.stock_quantity, p.stock_quantity)::int AS on_hand_quantity,
                    COALESCE(loc_sum.sellable_qty, 0)::int AS identifier_quantity,
                    (COALESCE(pv.stock_quantity, p.stock_quantity) - COALESCE(loc_sum.sellable_qty, 0))::int AS difference_quantity,
                    NULL::text AS identifier_value,
                    NULL::text AS identifier_status,
                    'Tồn bán được (' || COALESCE(pv.stock_quantity, p.stock_quantity) || ') không khớp với tổng tồn khả dụng tại các kệ bán hàng (' || COALESCE(loc_sum.sellable_qty, 0) || ').'::text AS message,
                    p.name || ' ' || COALESCE(p.sku, '') || ' ' || COALESCE(pv.sku, '') AS searchable_text
                FROM products p
                LEFT JOIN product_variants pv ON pv.product_id = p.id AND pv.deleted_at IS NULL
                LEFT JOIN (
                    SELECT
                        COALESCE(il.product_id, level_variant.product_id) AS product_id,
                        il.variant_id,
                        SUM(il.on_hand_quantity - il.reserved_quantity) AS sellable_qty
                    FROM inventory_levels il
                    LEFT JOIN product_variants level_variant ON level_variant.id = il.variant_id
                    JOIN inventory_locations loc ON loc.id = il.location_id
                    WHERE loc.purpose IN ('STORAGE', 'VIRTUAL') AND loc.status = 'ACTIVE'
                    GROUP BY COALESCE(il.product_id, level_variant.product_id), il.variant_id
                ) loc_sum ON loc_sum.product_id = p.id
                  AND (
                    (pv.id IS NOT NULL AND loc_sum.variant_id = pv.id)
                    OR (pv.id IS NULL AND loc_sum.variant_id IS NULL)
                  )
                WHERE p.deleted_at IS NULL
                  AND p.status <> 'MERGED'
                  AND COALESCE(pv.stock_quantity, p.stock_quantity) <> COALESCE(loc_sum.sellable_qty, 0)
            ),
            lot_quantity_mismatch AS (
                SELECT
                    'LOT_QUANTITY_MISMATCH'::text AS issue_type,
                    NULL::text AS identifier_type,
                    p.id::text AS product_id,
                    il.variant_id::text AS variant_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    pv.sku AS variant_sku,
                    pv.color_name AS variant_color,
                    pv.configuration AS variant_configuration,
                    il.location_id::text AS location_id,
                    loc.code AS location_code,
                    loc.name AS location_name,
                    il.on_hand_quantity::int AS on_hand_quantity,
                    COALESCE(lot_sum.lot_qty, 0)::int AS identifier_quantity,
                    (il.on_hand_quantity - COALESCE(lot_sum.lot_qty, 0))::int AS difference_quantity,
                    NULL::text AS identifier_value,
                    NULL::text AS identifier_status,
                    'Tồn kệ (' || il.on_hand_quantity || ') không khớp với tổng số lượng trong các lô hàng còn lại (' || COALESCE(lot_sum.lot_qty, 0) || ').'::text AS message,
                    p.name || ' ' || COALESCE(p.sku, '') || ' ' || COALESCE(pv.sku, '') || ' ' || loc.code AS searchable_text
                FROM inventory_levels il
                LEFT JOIN product_variants pv ON pv.id = il.variant_id
                JOIN products p ON p.id = COALESCE(il.product_id, pv.product_id)
                JOIN inventory_locations loc ON loc.id = il.location_id
                LEFT JOIN (
                    SELECT
                        product_id,
                        variant_id,
                        location_id,
                        SUM(remaining_quantity) AS lot_qty
                    FROM inventory_lots
                    GROUP BY product_id, variant_id, location_id
                ) lot_sum ON lot_sum.location_id = il.location_id
                  AND lot_sum.product_id = p.id
                  AND (
                    (il.variant_id IS NOT NULL AND lot_sum.variant_id = il.variant_id)
                    OR (il.variant_id IS NULL AND lot_sum.variant_id IS NULL)
                  )
                WHERE p.deleted_at IS NULL
                  AND p.status <> 'MERGED'
                  AND il.on_hand_quantity <> COALESCE(lot_sum.lot_qty, 0)
            ),
            reserved_quantity_mismatch AS (
                SELECT
                    'RESERVED_QUANTITY_MISMATCH'::text AS issue_type,
                    NULL::text AS identifier_type,
                    p.id::text AS product_id,
                    il.variant_id::text AS variant_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    pv.sku AS variant_sku,
                    pv.color_name AS variant_color,
                    pv.configuration AS variant_configuration,
                    il.location_id::text AS location_id,
                    loc.code AS location_code,
                    loc.name AS location_name,
                    il.reserved_quantity::int AS on_hand_quantity,
                    GREATEST(COALESCE(imei_res.reserved_cnt, 0), COALESCE(serial_res.reserved_cnt, 0))::int AS identifier_quantity,
                    (il.reserved_quantity - GREATEST(COALESCE(imei_res.reserved_cnt, 0), COALESCE(serial_res.reserved_cnt, 0)))::int AS difference_quantity,
                    NULL::text AS identifier_value,
                    NULL::text AS identifier_status,
                    'Lượng giữ chỗ reserved (' || il.reserved_quantity || ') không khớp với tổng số định danh đang RESERVED (' || GREATEST(COALESCE(imei_res.reserved_cnt, 0), COALESCE(serial_res.reserved_cnt, 0)) || ').'::text AS message,
                    p.name || ' ' || COALESCE(p.sku, '') || ' ' || COALESCE(pv.sku, '') || ' ' || loc.code AS searchable_text
                FROM inventory_levels il
                LEFT JOIN product_variants pv ON pv.id = il.variant_id
                JOIN products p ON p.id = COALESCE(il.product_id, pv.product_id)
                JOIN inventory_locations loc ON loc.id = il.location_id
                LEFT JOIN (
                    SELECT product_id, variant_id, location_id, COUNT(*) AS reserved_cnt
                    FROM product_imeis
                    WHERE status = 'RESERVED' AND location_id IS NOT NULL
                    GROUP BY product_id, variant_id, location_id
                ) imei_res ON imei_res.location_id = il.location_id
                  AND imei_res.product_id = p.id
                  AND (
                    (il.variant_id IS NOT NULL AND imei_res.variant_id = il.variant_id)
                    OR (il.variant_id IS NULL AND imei_res.variant_id IS NULL)
                  )
                LEFT JOIN (
                    SELECT product_id, variant_id, location_id, COUNT(*) AS reserved_cnt
                    FROM product_serial_numbers
                    WHERE status = 'RESERVED' AND location_id IS NOT NULL
                    GROUP BY product_id, variant_id, location_id
                ) serial_res ON serial_res.location_id = il.location_id
                  AND serial_res.product_id = p.id
                  AND (
                    (il.variant_id IS NOT NULL AND serial_res.variant_id = il.variant_id)
                    OR (il.variant_id IS NULL AND serial_res.variant_id IS NULL)
                  )
                WHERE p.deleted_at IS NULL
                  AND p.status <> 'MERGED'
                  AND (
                    il.reserved_quantity > 0
                    OR COALESCE(imei_res.reserved_cnt, 0) > 0
                    OR COALESCE(serial_res.reserved_cnt, 0) > 0
                  )
                  AND il.reserved_quantity <> GREATEST(COALESCE(imei_res.reserved_cnt, 0), COALESCE(serial_res.reserved_cnt, 0))
            ),
            identifier_pair_mismatch AS (
                SELECT
                    'IDENTIFIER_PAIR_MISMATCH'::text AS issue_type,
                    'IMEI'::text AS identifier_type,
                    p.id::text AS product_id,
                    pip.variant_id::text AS variant_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    pv.sku AS variant_sku,
                    pv.color_name AS variant_color,
                    pv.configuration AS variant_configuration,
                    NULL::text AS location_id,
                    NULL::text AS location_code,
                    NULL::text AS location_name,
                    NULL::int AS on_hand_quantity,
                    NULL::int AS identifier_quantity,
                    NULL::int AS difference_quantity,
                    pip.imei1 AS identifier_value,
                    NULL::text AS identifier_status,
                    'Cặp định danh ' || pip.imei1 || ' - ' || COALESCE(pip.serial_number, '') || ' có IMEI1 hoặc Serial bị lệch vị trí/trạng thái trong kho.'::text AS message,
                    p.name || ' ' || COALESCE(p.sku, '') || ' ' || COALESCE(pv.sku, '') || ' ' || pip.imei1 || ' ' || COALESCE(pip.serial_number, '') AS searchable_text
                FROM product_identifier_pairs pip
                LEFT JOIN product_variants pv ON pv.id = pip.variant_id
                JOIN products p ON p.id = COALESCE(pip.product_id, pv.product_id)
                LEFT JOIN product_imeis pi ON pi.imei = pip.imei1 AND pi.product_id = p.id
                LEFT JOIN product_serial_numbers psn ON psn.serial_number = pip.serial_number AND psn.product_id = p.id
                WHERE p.deleted_at IS NULL
                  AND p.status <> 'MERGED'
                  AND (
                    pi.id IS NULL
                    OR psn.id IS NULL
                    OR COALESCE(pi.location_id, '00000000-0000-0000-0000-000000000000'::uuid) <> COALESCE(psn.location_id, '00000000-0000-0000-0000-000000000000'::uuid)
                    OR pi.status <> psn.status
                  )
            ),
            document_ledger_mismatch AS (
                SELECT
                    'DOCUMENT_LEDGER_MISMATCH'::text AS issue_type,
                    NULL::text AS identifier_type,
                    NULL::text AS product_id,
                    NULL::text AS variant_id,
                    NULL::text AS product_name,
                    NULL::text AS product_sku,
                    NULL::text AS variant_sku,
                    NULL::text AS variant_color,
                    NULL::text AS variant_configuration,
                    NULL::text AS location_id,
                    NULL::text AS location_code,
                    NULL::text AS location_name,
                    NULL::int AS on_hand_quantity,
                    NULL::int AS identifier_quantity,
                    NULL::int AS difference_quantity,
                    d.document_no AS identifier_value,
                    d.status AS identifier_status,
                    'Chứng từ ' || d.document_type || ' (' || d.document_no || ') đã COMPLETED nhưng không thấy ghi nhận sổ kho.'::text AS message,
                    d.document_no || ' ' || d.document_type AS searchable_text
                FROM inventory_documents d
                LEFT JOIN inventory_adjustment_logs al
                  ON al.reference_code = d.document_no
                  OR COALESCE(al.note, '') LIKE '%' || d.document_no || '%'
                WHERE d.status = 'COMPLETED'
                  AND d.document_type IN ('INBOUND', 'OUTBOUND', 'TRANSFER', 'ADJUSTMENT')
                  AND al.id IS NULL
            ),
            issues AS (
                SELECT * FROM level_mismatches
                UNION ALL SELECT * FROM imei_without_location
                UNION ALL SELECT * FROM serial_without_location
                UNION ALL SELECT * FROM imei_without_level
                UNION ALL SELECT * FROM serial_without_level
                UNION ALL SELECT * FROM imei_terminal_with_location
                UNION ALL SELECT * FROM serial_terminal_with_location
                UNION ALL SELECT * FROM sellable_stock_mismatch
                UNION ALL SELECT * FROM lot_quantity_mismatch
                UNION ALL SELECT * FROM reserved_quantity_mismatch
                UNION ALL SELECT * FROM identifier_pair_mismatch
                UNION ALL SELECT * FROM document_ledger_mismatch
            )
            SELECT
                issue_type AS "issueType",
                identifier_type AS "identifierType",
                product_id AS "productId",
                variant_id AS "variantId",
                product_name AS "productName",
                product_sku AS "productSku",
                variant_sku AS "variantSku",
                variant_color AS "variantColor",
                variant_configuration AS "variantConfiguration",
                location_id AS "locationId",
                location_code AS "locationCode",
                location_name AS "locationName",
                on_hand_quantity AS "onHandQuantity",
                identifier_quantity AS "identifierQuantity",
                difference_quantity AS "differenceQuantity",
                identifier_value AS "identifierValue",
                identifier_status AS "identifierStatus",
                message
            FROM issues
            WHERE (:issue_type = '' OR issue_type = :issue_type)
              AND (
                :search = ''
                OR LOWER(searchable_text) LIKE LOWER(:pattern)
              )
            ORDER BY
                issue_type,
                product_name,
                COALESCE(variant_sku, product_sku),
                location_code NULLS LAST,
                identifier_value NULLS LAST
            """,
        ),
        {"search": search, "pattern": f"%{search}%", "issue_type": issue_type},
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
