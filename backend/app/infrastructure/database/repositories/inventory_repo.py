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
                p.stock_quantity AS "productStock",
                p.status AS "productStatus",
                p.sales_config AS "salesConfig",
                child.inventory_policy AS "childInventoryPolicy",
                parent.inventory_policy AS "parentInventoryPolicy",
                pv.id::text AS "variantId",
                pv.sku AS "variantSku",
                pv.configuration,
                pv.color_name AS "colorName",
                pv.stock_quantity AS "variantStock",
                COALESCE(vr.reserved_quantity, pr.reserved_quantity, 0) AS "reservationReservedQuantity",
                COALESCE(vi.reserved_quantity, pi.reserved_quantity, 0) AS "imeiReservedQuantity",
                COALESCE(vsnr.reserved_quantity, psnr.reserved_quantity, 0) AS "serialReservedQuantity",
                COALESCE(vlc.average_unit_cost, plc.average_unit_cost, 0) AS "averageUnitCost",
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


async def list_product_imeis_for_inventory(session: AsyncSession, product_id: UUID, variant_id: UUID | None) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                pi.id::text AS id,
                pi.imei AS value,
                pi.status,
                pi.is_primary AS "isPrimary",
                pi.source_reference AS "sourceReference",
                pi.received_at AS "receivedAt",
                pending.id::text AS "pendingRequestId",
                pending.new_value AS "pendingNewValue",
                pending.reason AS "pendingReason",
                pending.created_at AS "pendingCreatedAt"
            FROM product_imeis pi
            LEFT JOIN inventory_identifier_edit_requests pending
              ON pending.identifier_type = 'IMEI'
             AND pending.identifier_id = pi.id
             AND pending.status = 'PENDING'
            WHERE pi.product_id = :product_id
              AND (
                    (:variant_id_marker = 'BASE' AND pi.variant_id IS NULL)
                 OR (:variant_id_marker = 'VALUE' AND pi.variant_id = CAST(:variant_id AS UUID))
              )
            ORDER BY pi.status, pi.is_primary DESC, pi.received_at DESC, pi.imei
            """
        ),
        {"product_id": product_id, "variant_id": variant_id, "variant_id_marker": "VALUE" if variant_id else "BASE"},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_product_serial_numbers_for_inventory(session: AsyncSession, product_id: UUID, variant_id: UUID | None) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                psn.id::text AS id,
                psn.serial_number AS value,
                psn.status,
                psn.source_reference AS "sourceReference",
                psn.received_at AS "receivedAt",
                pending.id::text AS "pendingRequestId",
                pending.new_value AS "pendingNewValue",
                pending.reason AS "pendingReason",
                pending.created_at AS "pendingCreatedAt"
            FROM product_serial_numbers psn
            LEFT JOIN inventory_identifier_edit_requests pending
              ON pending.identifier_type = 'SERIAL'
             AND pending.identifier_id = psn.id
             AND pending.status = 'PENDING'
            WHERE psn.product_id = :product_id
              AND (
                    (:variant_id_marker = 'BASE' AND psn.variant_id IS NULL)
                 OR (:variant_id_marker = 'VALUE' AND psn.variant_id = CAST(:variant_id AS UUID))
              )
            ORDER BY psn.status, psn.received_at DESC, psn.serial_number
            """
        ),
        {"product_id": product_id, "variant_id": variant_id, "variant_id_marker": "VALUE" if variant_id else "BASE"},
    )
    return [dict(row) for row in result.mappings().all()]


async def get_identifier_for_edit(session: AsyncSession, identifier_type: str, identifier_id: UUID) -> dict | None:
    table_sql = (
        """
        SELECT id, product_id, variant_id, imei AS current_value, status
        FROM product_imeis
        WHERE id = :identifier_id
        FOR UPDATE
        """
        if identifier_type == "IMEI"
        else """
        SELECT id, product_id, variant_id, serial_number AS current_value, status
        FROM product_serial_numbers
        WHERE id = :identifier_id
        FOR UPDATE
        """
    )
    row = (await session.execute(text(table_sql), {"identifier_id": identifier_id})).mappings().first()
    return dict(row) if row else None


async def has_pending_identifier_edit_request(session: AsyncSession, identifier_type: str, identifier_id: UUID) -> bool:
    exists = await session.scalar(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM inventory_identifier_edit_requests
                WHERE identifier_type = :identifier_type
                  AND identifier_id = :identifier_id
                  AND status = 'PENDING'
            )
            """
        ),
        {"identifier_type": identifier_type, "identifier_id": identifier_id},
    )
    return bool(exists)


async def insert_identifier_edit_request(
    session: AsyncSession,
    *,
    request_id: UUID,
    identifier_type: str,
    identifier_id: UUID,
    product_id: UUID,
    variant_id: UUID | None,
    current_value: str,
    new_value: str,
    reason: str,
    requested_by: UUID | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_identifier_edit_requests (
                id, identifier_type, identifier_id, product_id, variant_id,
                current_value, new_value, reason, requested_by
            )
            VALUES (
                :id, :identifier_type, :identifier_id, :product_id, :variant_id,
                :current_value, :new_value, :reason, :requested_by
            )
            """
        ),
        {
            "id": request_id,
            "identifier_type": identifier_type,
            "identifier_id": identifier_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "current_value": current_value,
            "new_value": new_value,
            "reason": reason,
            "requested_by": requested_by,
        },
    )


async def get_identifier_edit_request_for_update(session: AsyncSession, request_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    id, identifier_type, identifier_id, product_id, variant_id,
                    current_value, new_value, reason, status
                FROM inventory_identifier_edit_requests
                WHERE id = :request_id
                FOR UPDATE
                """
            ),
            {"request_id": request_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_identifier_value(session: AsyncSession, identifier_type: str, identifier_id: UUID, new_value: str) -> None:
    if identifier_type == "IMEI":
        await session.execute(
            text("UPDATE product_imeis SET imei = :new_value, updated_at = NOW() WHERE id = :identifier_id"),
            {"identifier_id": identifier_id, "new_value": new_value},
        )
        return
    await session.execute(
        text("UPDATE product_serial_numbers SET serial_number = :new_value, updated_at = NOW() WHERE id = :identifier_id"),
        {"identifier_id": identifier_id, "new_value": new_value},
    )


async def update_identifier_edit_request_status(
    session: AsyncSession,
    *,
    request_id: UUID,
    status: str,
    decided_by: UUID | None,
    decision_note: str | None,
) -> None:
    await session.execute(
        text(
            """
            UPDATE inventory_identifier_edit_requests
            SET status = :status,
                decided_by = :decided_by,
                decided_at = NOW(),
                decision_note = :decision_note
            WHERE id = :request_id
            """
        ),
        {
            "request_id": request_id,
            "status": status,
            "decided_by": decided_by,
            "decision_note": decision_note,
        },
    )


async def list_identifier_edit_requests(
    session: AsyncSession,
    *,
    status: str | None = None,
    product_id: UUID | None = None,
    variant_id: UUID | None = None,
    limit: int = 100,
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                r.id::text AS id,
                r.identifier_type AS "identifierType",
                r.identifier_id::text AS "identifierId",
                r.product_id::text AS "productId",
                r.variant_id::text AS "variantId",
                p.name AS "productName",
                p.sku AS "productSku",
                pv.sku AS "variantSku",
                pv.color_name AS "variantColor",
                pv.configuration AS "variantConfiguration",
                r.current_value AS "currentValue",
                r.new_value AS "newValue",
                r.reason,
                r.status,
                r.requested_by::text AS "requestedBy",
                r.decided_by::text AS "decidedBy",
                r.decision_note AS "decisionNote",
                r.created_at AS "createdAt",
                r.decided_at AS "decidedAt"
            FROM inventory_identifier_edit_requests r
            JOIN products p ON p.id = r.product_id
            LEFT JOIN product_variants pv ON pv.id = r.variant_id
            WHERE (:status_marker = 'ALL' OR r.status = CAST(:status AS VARCHAR))
              AND (:product_id_marker = 'ALL' OR r.product_id = CAST(:product_id AS UUID))
              AND (
                    :variant_id_marker = 'ANY'
                 OR (:variant_id_marker = 'BASE' AND r.variant_id IS NULL)
                 OR (:variant_id_marker = 'VALUE' AND r.variant_id = CAST(:variant_id AS UUID))
              )
            ORDER BY
                CASE r.status WHEN 'PENDING' THEN 0 WHEN 'APPROVED' THEN 1 ELSE 2 END,
                r.created_at DESC
            LIMIT :limit
            """
        ),
        {
            "status": status,
            "status_marker": "VALUE" if status else "ALL",
            "product_id": product_id,
            "product_id_marker": "VALUE" if product_id else "ALL",
            "variant_id": variant_id,
            "variant_id_marker": "ANY" if product_id is None else "BASE" if variant_id is None else "VALUE",
            "limit": limit,
        },
    )
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_receipts(session: AsyncSession, search: str = "") -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                d.id::text AS id,
                d.document_no AS "referenceCode",
                d.status,
                d.reason AS "receiptReasonCode",
                d.supplier_name AS "supplierName",
                target.code AS "locationCode",
                target.name AS "locationName",
                d.note,
                d.created_at AS "createdAt",
                d.created_by::text AS "createdBy",
                MAX(CASE
                    WHEN d.created_by IS NULL AND d.document_no LIKE 'NK-KHOI-TAO-%' THEN 'Hệ thống'
                    ELSE COALESCE(NULLIF(created_user.full_name, ''), created_user.email)
                END) AS "createdByName",
                d.approved_at AS "approvedAt",
                d.approved_by::text AS "approvedBy",
                MAX(CASE
                    WHEN d.approved_by IS NULL AND d.document_no LIKE 'NK-KHOI-TAO-%' THEN 'Hệ thống'
                    ELSE COALESCE(NULLIF(approved_user.full_name, ''), approved_user.email)
                END) AS "approvedByName",
                d.posted_at AS "postedAt",
                d.posted_by::text AS "postedBy",
                MAX(CASE
                    WHEN d.posted_by IS NULL AND d.document_no LIKE 'NK-KHOI-TAO-%' THEN 'Hệ thống'
                    ELSE COALESCE(NULLIF(posted_user.full_name, ''), posted_user.email)
                END) AS "postedByName",
                d.cancelled_at AS "cancelledAt",
                d.cancelled_by::text AS "cancelledBy",
                MAX(COALESCE(NULLIF(cancelled_user.full_name, ''), cancelled_user.email)) AS "cancelledByName",
                d.reversed_at AS "reversedAt",
                d.reversed_by::text AS "reversedBy",
                MAX(COALESCE(NULLIF(reversed_user.full_name, ''), reversed_user.email)) AS "reversedByName",
                COUNT(l.id)::int AS "lineCount",
                COALESCE(SUM(l.requested_quantity), 0)::int AS "totalQuantity",
                COALESCE(SUM(COALESCE(l.unit_cost, 0) * l.requested_quantity), 0) AS "totalCost",
                jsonb_agg(
                    jsonb_build_object(
                        'id', l.id::text,
                        'productId', l.product_id::text,
                        'variantId', l.variant_id::text,
                        'productName', p.name,
                        'productSku', p.sku,
                        'variantSku', pv.sku,
                        'variantColor', pv.color_name,
                        'variantConfiguration', pv.configuration,
                        'quantity', l.requested_quantity,
                        'plannedQuantity', l.requested_quantity,
                        'receivedQuantity', COALESCE((l.metadata->>'receivedQuantity')::int, 0),
                        'tracksImei', COALESCE((l.metadata->>'tracksImei')::boolean, FALSE),
                        'tracksSerialNumber', COALESCE((l.metadata->>'tracksSerialNumber')::boolean, FALSE),
                        'imeis', COALESCE(l.metadata->'imeis', '[]'::jsonb),
                        'serialNumbers', COALESCE(l.metadata->'serialNumbers', '[]'::jsonb),
                        'imeiCount', jsonb_array_length(COALESCE(l.metadata->'imeis', '[]'::jsonb)),
                        'serialNumberCount', jsonb_array_length(COALESCE(l.metadata->'serialNumbers', '[]'::jsonb)),
                        'shortageReason', l.metadata->>'shortageReason',
                        'unitCost', l.unit_cost,
                        'note', l.note
                    )
                    ORDER BY l.created_at, p.name, pv.sku
                ) AS lines
            FROM inventory_documents d
            JOIN inventory_document_lines l ON l.document_id = d.id
            JOIN products p ON p.id = l.product_id
            LEFT JOIN product_variants pv ON pv.id = l.variant_id
            LEFT JOIN inventory_locations target ON target.id = d.target_location_id
            LEFT JOIN users created_user ON created_user.id = d.created_by
            LEFT JOIN users approved_user ON approved_user.id = d.approved_by
            LEFT JOIN users posted_user ON posted_user.id = d.posted_by
            LEFT JOIN users cancelled_user ON cancelled_user.id = d.cancelled_by
            LEFT JOIN users reversed_user ON reversed_user.id = d.reversed_by
            WHERE d.document_type = 'INBOUND'
              AND p.deleted_at IS NULL
              AND p.status <> 'MERGED'
              AND (:search = ''
                OR LOWER(COALESCE(d.document_no, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.supplier_name, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.reason, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.status, '')) LIKE LOWER(:pattern)
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(p.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
              )
            GROUP BY d.id, target.code, target.name
            ORDER BY d.created_at DESC
            LIMIT 200
            """
        ),
        {"search": search, "pattern": f"%{search}%"},
    )
    document_rows = [dict(row) for row in result.mappings().all()]
    legacy_result = await session.execute(
        text(
            """
            SELECT
                ial.reference_code AS "referenceCode",
                'COMPLETED' AS status,
                COALESCE(MAX(NULLIF(ial.reason, '')), 'NK_MUA') AS "receiptReasonCode",
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
              AND p.deleted_at IS NULL
              AND p.status <> 'MERGED'
              AND NOT EXISTS (
                SELECT 1
                FROM inventory_documents d
                WHERE d.document_type = 'INBOUND'
                  AND d.document_no = ial.reference_code
              )
              AND (:search = ''
                OR LOWER(COALESCE(ial.reference_code, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(ial.supplier_name, '')) LIKE LOWER(:pattern)
                OR LOWER('COMPLETED') LIKE LOWER(:pattern)
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
    legacy_rows = [dict(row) for row in legacy_result.mappings().all()]
    return sorted(document_rows + legacy_rows, key=lambda row: row.get("createdAt") or "", reverse=True)[:200]


async def list_inventory_stock_counts(session: AsyncSession, search: str = "") -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                d.id::text AS id,
                d.document_no AS "referenceCode",
                d.status,
                d.reason,
                d.note,
                target.code AS "locationCode",
                target.name AS "locationName",
                d.created_at AS "createdAt",
                d.created_by::text AS "createdBy",
                d.approved_at AS "approvedAt",
                d.approved_by::text AS "approvedBy",
                d.cancelled_at AS "cancelledAt",
                d.cancelled_by::text AS "cancelledBy",
                COUNT(l.id)::int AS "lineCount",
                COALESCE(SUM(ABS(COALESCE(l.variance_quantity, 0))), 0)::int AS "absoluteVarianceQuantity",
                COALESCE(SUM(COALESCE(l.variance_quantity, 0)), 0)::int AS "netVarianceQuantity",
                jsonb_agg(
                    jsonb_build_object(
                        'id', l.id::text,
                        'productId', l.product_id::text,
                        'variantId', l.variant_id::text,
                        'productName', p.name,
                        'productSku', p.sku,
                        'variantSku', pv.sku,
                        'variantColor', pv.color_name,
                        'variantConfiguration', pv.configuration,
                        'expectedQuantity', COALESCE(l.expected_quantity, 0),
                        'countedQuantity', COALESCE(l.counted_quantity, 0),
                        'varianceQuantity', COALESCE(l.variance_quantity, 0),
                        'note', l.note
                    )
                    ORDER BY l.created_at, p.name, pv.sku
                ) AS lines
            FROM inventory_documents d
            JOIN inventory_document_lines l ON l.document_id = d.id
            JOIN products p ON p.id = l.product_id
            LEFT JOIN product_variants pv ON pv.id = l.variant_id
            LEFT JOIN inventory_locations target ON target.id = d.target_location_id
            WHERE d.document_type = 'COUNT'
              AND (:search = ''
                OR LOWER(COALESCE(d.document_no, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.status, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.reason, '')) LIKE LOWER(:pattern)
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(p.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
              )
            GROUP BY d.id, target.code, target.name
            ORDER BY d.created_at DESC
            LIMIT 100
            """
        ),
        {"search": search, "pattern": f"%{search}%"},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_adjustments(session: AsyncSession, search: str = "") -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                d.id::text AS id,
                d.document_no AS "referenceCode",
                d.status,
                d.reason,
                d.note,
                target.code AS "locationCode",
                target.name AS "locationName",
                d.created_at AS "createdAt",
                d.created_by::text AS "createdBy",
                d.approved_at AS "approvedAt",
                d.approved_by::text AS "approvedBy",
                d.cancelled_at AS "cancelledAt",
                d.cancelled_by::text AS "cancelledBy",
                COUNT(l.id)::int AS "lineCount",
                COALESCE(SUM(ABS(COALESCE(l.variance_quantity, 0))), 0)::int AS "absoluteVarianceQuantity",
                COALESCE(SUM(COALESCE(l.variance_quantity, 0)), 0)::int AS "netVarianceQuantity",
                jsonb_agg(
                    jsonb_build_object(
                        'id', l.id::text,
                        'productId', l.product_id::text,
                        'variantId', l.variant_id::text,
                        'productName', p.name,
                        'productSku', p.sku,
                        'variantSku', pv.sku,
                        'variantColor', pv.color_name,
                        'variantConfiguration', pv.configuration,
                        'currentQuantity', COALESCE(l.expected_quantity, 0),
                        'newQuantity', COALESCE(l.counted_quantity, 0),
                        'varianceQuantity', COALESCE(l.variance_quantity, 0),
                        'reason', COALESCE(l.metadata->>'adjustmentReason', d.reason),
                        'note', l.note
                    )
                    ORDER BY l.created_at, p.name, pv.sku
                ) AS lines
            FROM inventory_documents d
            JOIN inventory_document_lines l ON l.document_id = d.id
            JOIN products p ON p.id = l.product_id
            LEFT JOIN product_variants pv ON pv.id = l.variant_id
            LEFT JOIN inventory_locations target ON target.id = d.target_location_id
            WHERE d.document_type = 'ADJUSTMENT'
              AND (:search = ''
                OR LOWER(COALESCE(d.document_no, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.status, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.reason, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(l.metadata->>'adjustmentReason', '')) LIKE LOWER(:pattern)
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(p.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
              )
            GROUP BY d.id, target.code, target.name
            ORDER BY d.created_at DESC
            LIMIT 100
            """
        ),
        {"search": search, "pattern": f"%{search}%"},
    )
    return [dict(row) for row in result.mappings().all()]


async def insert_inventory_stock_count_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    reference_code: str,
    reason: str,
    note: str | None,
    location_id: UUID,
    created_by: UUID | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status, target_location_id,
                reference_code, reason, note, created_by
            )
            VALUES (
                :id, :document_no, 'COUNT', 'DRAFT', :target_location_id,
                :reference_code, :reason, :note, :created_by
            )
            """
        ),
        {
            "id": document_id,
            "document_no": reference_code,
            "reference_code": reference_code,
            "reason": reason,
            "note": note,
            "target_location_id": location_id,
            "created_by": created_by,
        },
    )


async def insert_inventory_adjustment_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    reference_code: str,
    reason: str,
    note: str | None,
    location_id: UUID,
    created_by: UUID | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status, target_location_id,
                reference_code, reason, note, created_by
            )
            VALUES (
                :id, :document_no, 'ADJUSTMENT', 'DRAFT', :target_location_id,
                :reference_code, :reason, :note, :created_by
            )
            """
        ),
        {
            "id": document_id,
            "document_no": reference_code,
            "reference_code": reference_code,
            "reason": reason,
            "note": note,
            "target_location_id": location_id,
            "created_by": created_by,
        },
    )


async def insert_inventory_stock_count_line(
    session: AsyncSession,
    *,
    line_id: UUID,
    document_id: UUID,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    expected_quantity: int,
    counted_quantity: int,
    note: str | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_document_lines (
                id, document_id, product_id, variant_id, location_id,
                requested_quantity, expected_quantity, counted_quantity,
                variance_quantity, note, metadata
            )
            VALUES (
                :id, :document_id, :product_id, :variant_id, :location_id,
                0, :expected_quantity, :counted_quantity,
                :variance_quantity, :note, '{}'::jsonb
            )
            """
        ),
        {
            "id": line_id,
            "document_id": document_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "expected_quantity": expected_quantity,
            "counted_quantity": counted_quantity,
            "variance_quantity": counted_quantity - expected_quantity,
            "note": note,
        },
    )


async def insert_inventory_adjustment_line(
    session: AsyncSession,
    *,
    line_id: UUID,
    document_id: UUID,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    current_quantity: int,
    new_quantity: int,
    reason: str,
    note: str | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_document_lines (
                id, document_id, product_id, variant_id, location_id,
                requested_quantity, expected_quantity, counted_quantity,
                variance_quantity, note, metadata
            )
            VALUES (
                :id, :document_id, :product_id, :variant_id, :location_id,
                0, :current_quantity, :new_quantity,
                :variance_quantity, :note, jsonb_build_object('adjustmentReason', CAST(:reason AS TEXT))
            )
            """
        ),
        {
            "id": line_id,
            "document_id": document_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "current_quantity": current_quantity,
            "new_quantity": new_quantity,
            "variance_quantity": new_quantity - current_quantity,
            "reason": reason,
            "note": note,
        },
    )


async def get_inventory_stock_count_for_update(session: AsyncSession, reference_code: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    d.id,
                    d.document_no,
                    d.status,
                    d.reason,
                    d.note,
                    d.target_location_id,
                    target.code AS "locationCode",
                    target.name AS "locationName"
                FROM inventory_documents d
                LEFT JOIN inventory_locations target ON target.id = d.target_location_id
                WHERE d.document_type = 'COUNT' AND d.document_no = :reference_code
                FOR UPDATE
                """
            ),
            {"reference_code": reference_code},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_inventory_adjustment_for_update(session: AsyncSession, reference_code: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    d.id,
                    d.document_no,
                    d.status,
                    d.reason,
                    d.note,
                    d.target_location_id,
                    target.code AS "locationCode",
                    target.name AS "locationName"
                FROM inventory_documents d
                LEFT JOIN inventory_locations target ON target.id = d.target_location_id
                WHERE d.document_type = 'ADJUSTMENT' AND d.document_no = :reference_code
                FOR UPDATE OF d
                """
            ),
            {"reference_code": reference_code},
        )
    ).mappings().first()
    return dict(row) if row else None


async def list_inventory_stock_count_lines(session: AsyncSession, document_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                l.id,
                l.product_id AS "productId",
                l.variant_id AS "variantId",
                COALESCE(l.expected_quantity, 0) AS "expectedQuantity",
                COALESCE(l.counted_quantity, 0) AS "countedQuantity",
                COALESCE(l.variance_quantity, 0) AS "varianceQuantity",
                l.note
            FROM inventory_document_lines l
            WHERE l.document_id = :document_id
            ORDER BY l.created_at, l.id
            """
        ),
        {"document_id": document_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_adjustment_lines(session: AsyncSession, document_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                l.id,
                l.product_id AS "productId",
                l.variant_id AS "variantId",
                COALESCE(l.expected_quantity, 0) AS "currentQuantity",
                COALESCE(l.counted_quantity, 0) AS "newQuantity",
                COALESCE(l.variance_quantity, 0) AS "varianceQuantity",
                COALESCE(l.metadata->>'adjustmentReason', '') AS reason,
                l.note
            FROM inventory_document_lines l
            WHERE l.document_id = :document_id
            ORDER BY l.created_at, l.id
            """
        ),
        {"document_id": document_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def get_inventory_location_by_code(session: AsyncSession, code: str) -> dict | None:
    row = (
        await session.execute(
            text("SELECT id, code, name FROM inventory_locations WHERE code = :code"),
            {"code": code},
        )
    ).mappings().first()
    return dict(row) if row else None


async def ensure_inventory_location(session: AsyncSession, *, code: str, name: str) -> dict:
    await session.execute(
        text(
            """
            INSERT INTO inventory_locations (code, name, location_type, status, is_default)
            VALUES (:code, :name, 'WAREHOUSE', 'ACTIVE', :is_default)
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                status = 'ACTIVE',
                updated_at = NOW()
            """
        ),
        {"code": code, "name": name, "is_default": code == "MAIN"},
    )
    row = await get_inventory_location_by_code(session, code)
    if not row:
        raise RuntimeError("Inventory location was not created.")
    return row


async def get_inventory_receipt_for_update(session: AsyncSession, reference_code: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    d.id,
                    d.document_no,
                    d.status,
                    d.reason,
                    d.supplier_name,
                    d.note,
                    d.target_location_id,
                    d.posted_at,
                    d.created_by,
                    d.approved_by,
                    d.posted_by,
                    d.cancelled_by,
                    d.reversed_by,
                    d.reversal_of_document_id,
                    target.code AS "locationCode",
                    target.name AS "locationName"
                FROM inventory_documents d
                LEFT JOIN inventory_locations target ON target.id = d.target_location_id
                WHERE d.document_type = 'INBOUND' AND d.document_no = :reference_code
                FOR UPDATE OF d
                """
            ),
            {"reference_code": reference_code},
        )
    ).mappings().first()
    return dict(row) if row else None


async def inventory_receipt_has_reversal(session: AsyncSession, document_id: UUID) -> bool:
    exists = await session.scalar(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM inventory_documents
                WHERE document_type = 'REVERSAL'
                  AND reversal_of_document_id = :document_id
            )
            """
        ),
        {"document_id": document_id},
    )
    return bool(exists)


async def insert_inventory_receipt_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    reference_code: str,
    status: str,
    reason: str,
    supplier_name: str | None,
    note: str | None,
    location_id: UUID,
    created_by: UUID | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status, target_location_id,
                supplier_name, reference_code, reason, note, created_by
            )
            VALUES (
                :id, :document_no, 'INBOUND', :status, :target_location_id,
                :supplier_name, :reference_code, :reason, :note, :created_by
            )
            """
        ),
        {
            "id": document_id,
            "document_no": reference_code,
            "status": status,
            "reason": reason,
            "target_location_id": location_id,
            "supplier_name": supplier_name,
            "reference_code": reference_code,
            "note": note,
            "created_by": created_by,
        },
    )


async def update_inventory_receipt_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    reason: str,
    supplier_name: str | None,
    note: str | None,
    location_id: UUID,
) -> None:
    await session.execute(
        text(
            """
            UPDATE inventory_documents
            SET status = 'DRAFT',
                target_location_id = :target_location_id,
                supplier_name = :supplier_name,
                reason = :reason,
                note = :note,
                approved_at = NULL,
                approved_by = NULL,
                cancelled_at = NULL,
                cancelled_by = NULL
            WHERE id = :document_id
            """
        ),
        {
            "document_id": document_id,
            "target_location_id": location_id,
            "supplier_name": supplier_name,
            "reason": reason,
            "note": note,
        },
    )


async def insert_inventory_reversal_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    reference_code: str,
    original_document_id: UUID,
    reason: str,
    note: str | None,
    location_id: UUID | None,
    created_by: UUID | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status, source_location_id,
                reference_code, reason, note, created_by, approved_by, posted_by,
                approved_at, posted_at, reversal_of_document_id
            )
            VALUES (
                :id, :document_no, 'REVERSAL', 'COMPLETED', :source_location_id,
                :reference_code, :reason, :note, :created_by, :created_by, :created_by,
                NOW(), NOW(), :reversal_of_document_id
            )
            """
        ),
        {
            "id": document_id,
            "document_no": reference_code,
            "source_location_id": location_id,
            "reference_code": reference_code,
            "reason": reason,
            "note": note,
            "created_by": created_by,
            "reversal_of_document_id": original_document_id,
        },
    )


async def insert_inventory_receipt_line(
    session: AsyncSession,
    *,
    line_id: UUID,
    document_id: UUID,
    product_id: UUID,
    variant_id: UUID,
    location_id: UUID,
    quantity: int,
    unit_cost: float | None,
    note: str | None,
    imeis: list[str],
    tracks_imei: bool,
    serial_numbers: list[str],
    tracks_serial_number: bool,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_document_lines (
                id, document_id, product_id, variant_id, location_id,
                requested_quantity, expected_quantity, unit_cost, note, metadata
            )
            VALUES (
                :id, :document_id, :product_id, :variant_id, :location_id,
                :quantity, :quantity, :unit_cost, :note, CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "id": line_id,
            "document_id": document_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "quantity": quantity,
            "unit_cost": unit_cost,
            "note": note,
            "metadata": json.dumps(
                {
                    "imeis": imeis,
                    "tracksImei": tracks_imei,
                    "serialNumbers": serial_numbers,
                    "tracksSerialNumber": tracks_serial_number,
                    "plannedQuantity": quantity,
                    "receivedQuantity": len(imeis) if tracks_imei else len(serial_numbers) if tracks_serial_number else quantity,
                },
                ensure_ascii=False,
            ),
        },
    )


async def list_inventory_receipt_lines(session: AsyncSession, document_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                l.id,
                l.product_id AS "productId",
                l.variant_id AS "variantId",
                l.requested_quantity AS quantity,
                l.unit_cost AS "unitCost",
                l.note,
                COALESCE(l.metadata->'imeis', '[]'::jsonb) AS imeis,
                COALESCE(l.metadata->'serialNumbers', '[]'::jsonb) AS "serialNumbers",
                COALESCE((l.metadata->>'tracksImei')::boolean, FALSE) AS "tracksImei",
                COALESCE((l.metadata->>'tracksSerialNumber')::boolean, FALSE) AS "tracksSerialNumber",
                COALESCE((l.metadata->>'receivedQuantity')::int, 0) AS "receivedQuantity",
                l.metadata->>'shortageReason' AS "shortageReason"
            FROM inventory_document_lines l
            WHERE l.document_id = :document_id
            ORDER BY l.created_at, l.id
            """
        ),
        {"document_id": document_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def delete_inventory_receipt_lines(session: AsyncSession, document_id: UUID) -> None:
    await session.execute(
        text("DELETE FROM inventory_document_lines WHERE document_id = :document_id"),
        {"document_id": document_id},
    )


async def delete_inventory_receipt_document(session: AsyncSession, document_id: UUID) -> None:
    await session.execute(
        text("DELETE FROM inventory_documents WHERE id = :document_id"),
        {"document_id": document_id},
    )


async def list_imei_statuses(session: AsyncSession, imeis: list[str]) -> list[dict]:
    if not imeis:
        return []
    rows = (
        await session.execute(
            text(
                """
                SELECT imei, status
                FROM product_imeis
                WHERE imei = ANY(:imeis)
                FOR UPDATE
                """
            ),
            {"imeis": imeis},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def list_serial_number_statuses(session: AsyncSession, serial_numbers: list[str]) -> list[dict]:
    if not serial_numbers:
        return []
    rows = (
        await session.execute(
            text(
                """
                SELECT serial_number, status
                FROM product_serial_numbers
                WHERE serial_number = ANY(:serial_numbers)
                FOR UPDATE
                """
            ),
            {"serial_numbers": serial_numbers},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def list_product_serial_number_statuses(session: AsyncSession, *, product_id: UUID, serial_numbers: list[str]) -> list[dict]:
    if not serial_numbers:
        return []
    rows = (
        await session.execute(
            text(
                """
                SELECT serial_number, status
                FROM product_serial_numbers
                WHERE product_id = :product_id
                  AND serial_number = ANY(:serial_numbers)
                FOR UPDATE
                """
            ),
            {"product_id": product_id, "serial_numbers": serial_numbers},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def mark_imeis_reversed(session: AsyncSession, imeis: list[str]) -> None:
    if not imeis:
        return
    await session.execute(
        text(
            """
            UPDATE product_imeis
            SET status = 'REVERSED',
                is_primary = FALSE,
                updated_at = NOW()
            WHERE imei = ANY(:imeis)
            """
        ),
        {"imeis": imeis},
    )


async def mark_serial_numbers_reversed(session: AsyncSession, serial_numbers: list[str], product_id: UUID | None = None) -> None:
    if not serial_numbers:
        return
    product_filter = "AND product_id = :product_id" if product_id else ""
    await session.execute(
        text(
            f"""
            UPDATE product_serial_numbers
            SET status = 'REVERSED',
                updated_at = NOW()
            WHERE serial_number = ANY(:serial_numbers)
            {product_filter}
            """
        ),
        {"serial_numbers": serial_numbers, "product_id": product_id},
    )


async def update_inventory_receipt_line_imeis(
    session: AsyncSession,
    *,
    line_id: UUID,
    imeis: list[str],
    serial_numbers: list[str],
    received_quantity: int,
    shortage_reason: str | None,
) -> None:
    await session.execute(
        text(
            """
            UPDATE inventory_document_lines
            SET metadata = metadata
                || jsonb_build_object(
                    'imeis', CAST(:imeis AS jsonb),
                    'serialNumbers', CAST(:serial_numbers AS jsonb),
                    'receivedQuantity', CAST(:received_quantity AS INTEGER),
                    'shortageReason', CAST(:shortage_reason AS TEXT)
                )
            WHERE id = :line_id
            """
        ),
        {
            "line_id": line_id,
            "imeis": json.dumps(imeis, ensure_ascii=False),
            "serial_numbers": json.dumps(serial_numbers, ensure_ascii=False),
            "received_quantity": received_quantity,
            "shortage_reason": shortage_reason,
        },
    )


async def mark_inventory_receipt_reversed(
    session: AsyncSession,
    *,
    document_id: UUID,
    actor_id: UUID | None,
    note: str | None = None,
) -> None:
    await session.execute(
        text(
            """
            UPDATE inventory_documents
            SET status = 'REVERSED',
                note = COALESCE(:note, note),
                reversed_at = CASE WHEN reversed_at IS NULL THEN NOW() ELSE reversed_at END,
                reversed_by = CASE WHEN reversed_by IS NULL THEN :actor_id ELSE reversed_by END
            WHERE id = :document_id
            """
        ),
        {"document_id": document_id, "actor_id": actor_id, "note": note},
    )


async def update_inventory_receipt_status(
    session: AsyncSession,
    *,
    document_id: UUID,
    status: str,
    note: str | None = None,
    actor_id: UUID | None = None,
) -> None:
    await session.execute(
        text(
            """
            UPDATE inventory_documents
            SET status = CAST(:status AS VARCHAR),
                note = COALESCE(:note, note),
                approved_at = CASE WHEN CAST(:status AS VARCHAR) = 'APPROVED' AND approved_at IS NULL THEN NOW() ELSE approved_at END,
                approved_by = CASE WHEN CAST(:status AS VARCHAR) = 'APPROVED' AND approved_by IS NULL THEN :actor_id ELSE approved_by END,
                posted_at = CASE WHEN CAST(:status AS VARCHAR) = 'COMPLETED' AND posted_at IS NULL THEN NOW() ELSE posted_at END,
                posted_by = CASE WHEN CAST(:status AS VARCHAR) = 'COMPLETED' AND posted_by IS NULL THEN :actor_id ELSE posted_by END,
                cancelled_at = CASE WHEN CAST(:status AS VARCHAR) = 'CANCELLED' AND cancelled_at IS NULL THEN NOW() ELSE cancelled_at END,
                cancelled_by = CASE WHEN CAST(:status AS VARCHAR) = 'CANCELLED' AND cancelled_by IS NULL THEN :actor_id ELSE cancelled_by END
            WHERE id = :document_id
            """
        ),
        {"document_id": document_id, "status": status, "note": note, "actor_id": actor_id},
    )


async def insert_inventory_receipt_audit_log(
    session: AsyncSession,
    *,
    actor_id: UUID | None,
    action: str,
    reference_code: str,
    metadata: dict,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs (user_id, event_type, ip_address, user_agent, metadata)
            VALUES (:actor_id, :event_type, 'system', NULL, CAST(:metadata AS jsonb))
            """
        ),
        {
            "actor_id": actor_id,
            "event_type": f"inventory_receipt_{action}",
            "metadata": json.dumps(
                {
                    "referenceCode": reference_code,
                    **metadata,
                },
                ensure_ascii=False,
            ),
        },
    )


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
            text(
                """
                SELECT id
                FROM product_variants
                WHERE product_id = :product_id
                  AND deleted_at IS NULL
                  AND is_active = TRUE
                  AND COALESCE(status, 'active') NOT IN ('deleted', 'archived')
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def get_product_receipt_eligibility_for_update(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    p.id,
                    p.name,
                    p.sku,
                    p.status,
                    p.deleted_at,
                    p.hidden_by_category,
                    p.hidden_by_brand,
                    EXISTS (
                        SELECT 1
                        FROM products revision
                        WHERE revision.parent_product_id = p.id
                          AND revision.deleted_at IS NULL
                          AND revision.status IN ('REVISION_DRAFT', 'PENDING')
                    ) AS has_pending_revision
                FROM products p
                WHERE p.id = :product_id
                FOR UPDATE
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_variant_inventory_for_update(session: AsyncSession, *, product_id: UUID, variant_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, stock_quantity, sku
                FROM product_variants
                WHERE id = :variant_id
                  AND product_id = :product_id
                  AND deleted_at IS NULL
                  AND is_active = TRUE
                  AND COALESCE(status, 'active') NOT IN ('deleted', 'archived')
                FOR UPDATE
                """
            ),
            {"variant_id": variant_id, "product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_product_stock_for_update(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, stock_quantity, sku
                FROM products
                WHERE id = :product_id
                FOR UPDATE
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_product_stock(session: AsyncSession, *, product_id: UUID, quantity: int) -> None:
    await session.execute(
        text("UPDATE products SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
        {"id": product_id, "quantity": quantity},
    )


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


async def list_existing_serial_numbers(session: AsyncSession, serial_numbers: list[str], product_id: UUID | None = None) -> list[str]:
    if not serial_numbers:
        return []
    product_filter = "AND product_id = :product_id" if product_id else ""
    rows = (
        await session.execute(
            text(f"""
                SELECT serial_number
                FROM product_serial_numbers
                WHERE serial_number = ANY(:serial_numbers)
                {product_filter}
            """),
            {"serial_numbers": serial_numbers, "product_id": product_id},
        )
    ).mappings().all()
    return [str(row["serial_number"]) for row in rows]


async def update_variant_stock(session: AsyncSession, *, variant_id: UUID, quantity: int) -> None:
    await session.execute(
        text("UPDATE product_variants SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
        {"id": variant_id, "quantity": quantity},
    )


async def post_inventory_level_receipt(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID,
    location_id: UUID,
    quantity: int,
    unit_cost: float | int | None,
) -> None:
    await session.execute(
        text(
            """
            WITH updated AS (
                UPDATE inventory_levels
                SET average_unit_cost = CASE
                        WHEN on_hand_quantity + :quantity <= 0 THEN average_unit_cost
                        WHEN CAST(:unit_cost AS NUMERIC) IS NULL THEN average_unit_cost
                        ELSE ROUND(
                            (
                                on_hand_quantity * average_unit_cost
                                + :quantity * CAST(:unit_cost AS NUMERIC)
                            ) / NULLIF(on_hand_quantity + :quantity, 0),
                            2
                        )
                    END,
                    on_hand_quantity = on_hand_quantity + :quantity,
                    updated_at = NOW()
                WHERE product_id IS NULL
                  AND variant_id = :variant_id
                  AND location_id = :location_id
                RETURNING id
            )
            INSERT INTO inventory_levels (
                id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost
            )
            SELECT
                gen_random_uuid(),
                NULL,
                :variant_id,
                :location_id,
                :quantity,
                0,
                COALESCE(CAST(:unit_cost AS NUMERIC), 0)
            WHERE NOT EXISTS (SELECT 1 FROM updated)
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "quantity": quantity,
            "unit_cost": unit_cost,
        },
    )


async def post_inventory_level_reversal(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID,
    location_id: UUID,
    quantity: int,
) -> None:
    await session.execute(
        text(
            """
            UPDATE inventory_levels
            SET on_hand_quantity = GREATEST(on_hand_quantity - :quantity, 0),
                updated_at = NOW()
            WHERE product_id IS NULL
              AND variant_id = :variant_id
              AND location_id = :location_id
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "quantity": quantity,
        },
    )


async def set_inventory_level_counted_quantity(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    counted_quantity: int,
) -> None:
    if variant_id:
        await session.execute(
            text(
                """
                WITH updated AS (
                    UPDATE inventory_levels
                    SET on_hand_quantity = :counted_quantity,
                        last_counted_at = NOW(),
                        updated_at = NOW()
                    WHERE product_id IS NULL
                      AND variant_id = :variant_id
                      AND location_id = :location_id
                    RETURNING id
                )
                INSERT INTO inventory_levels (
                    id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost, last_counted_at
                )
                SELECT gen_random_uuid(), NULL, :variant_id, :location_id, :counted_quantity, 0, 0, NOW()
                WHERE NOT EXISTS (SELECT 1 FROM updated)
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "location_id": location_id,
                "counted_quantity": counted_quantity,
            },
        )
        return
    await session.execute(
        text(
            """
            WITH updated AS (
                UPDATE inventory_levels
                SET on_hand_quantity = :counted_quantity,
                    last_counted_at = NOW(),
                    updated_at = NOW()
                WHERE product_id = :product_id
                  AND variant_id IS NULL
                  AND location_id = :location_id
                RETURNING id
            )
            INSERT INTO inventory_levels (
                id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost, last_counted_at
            )
            SELECT gen_random_uuid(), :product_id, NULL, :location_id, :counted_quantity, 0, 0, NOW()
            WHERE NOT EXISTS (SELECT 1 FROM updated)
            """
        ),
        {
            "product_id": product_id,
            "location_id": location_id,
            "counted_quantity": counted_quantity,
        },
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
                id, product_id, variant_id, imei, is_primary, status, source_reference, received_at
            )
            VALUES (
                :id,
                :product_id,
                :variant_id,
                :imei,
                NOT EXISTS (
                    SELECT 1
                    FROM product_imeis existing
                    WHERE existing.product_id = :product_id
                      AND (
                          existing.variant_id = :variant_id
                          OR (existing.variant_id IS NULL AND :variant_id IS NULL)
                      )
                      AND existing.is_primary = TRUE
                ),
                'IN_STOCK',
                :source_reference,
                NOW()
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


async def insert_product_serial_number(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID,
    serial_number: str,
    source_reference: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (
                id, product_id, variant_id, serial_number, status, source_reference, received_at
            )
            VALUES (
                :id, :product_id, :variant_id, :serial_number, 'IN_STOCK', :source_reference, NOW()
            )
            ON CONFLICT (product_id, serial_number) DO NOTHING
            """
        ),
        {
            "id": uuid4(),
            "product_id": product_id,
            "variant_id": variant_id,
            "serial_number": serial_number,
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
        {"key": key, "product_id": product_id, "response_payload": json.dumps(response_payload, ensure_ascii=False)},
    )
