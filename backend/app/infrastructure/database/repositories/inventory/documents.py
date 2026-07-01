import json
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_inventory_receipts(
    session: AsyncSession,
    search: str = "",
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                d.id::text AS id,
                d.document_no AS "referenceCode",
                d.status,
                d.reason AS "receiptReasonCode",
                d.supplier_name AS "supplierName",
                COALESCE(d.metadata->'attachments', '[]'::jsonb) AS attachments,
                COALESCE(d.metadata->'discrepancies', '[]'::jsonb) AS discrepancies,
                COALESCE(d.metadata->>'qualityStatus', 'PENDING') AS "qualityStatus",
                d.metadata->>'qualityNote' AS "qualityNote",
                COALESCE((d.metadata->>'quarantine')::boolean, FALSE) AS quarantine,
                d.metadata->>'quarantineLocation' AS "quarantineLocation",
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
                        'storageLocationCode', l.metadata->>'storageLocationCode',
                        'storageLocationName', l.metadata->>'storageLocationName',
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
              AND (:date_from = '' OR d.created_at >= CAST(NULLIF(:date_from, '') AS date))
              AND (:date_to = '' OR d.created_at < CAST(NULLIF(:date_to, '') AS date) + INTERVAL '1 day')
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
            """
        ),
        {"search": search, "pattern": f"%{search}%", "date_from": date_from, "date_to": date_to},
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
              AND (:date_from = '' OR ial.created_at >= CAST(NULLIF(:date_from, '') AS date))
              AND (:date_to = '' OR ial.created_at < CAST(NULLIF(:date_to, '') AS date) + INTERVAL '1 day')
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
            """
        ),
        {"search": search, "pattern": f"%{search}%", "date_from": date_from, "date_to": date_to},
    )
    legacy_rows = [dict(row) for row in legacy_result.mappings().all()]
    return sorted(document_rows + legacy_rows, key=lambda row: row.get("createdAt") or "", reverse=True)


async def get_inventory_receipt_report(session: AsyncSession) -> dict:
    monthly_rows = await session.execute(
        text(
            """
            SELECT
                to_char(date_trunc('month', d.created_at), 'YYYY-MM') AS period,
                COUNT(*)::int AS "receiptCount",
                COALESCE(SUM(line_totals.total_quantity), 0)::int AS "totalQuantity",
                COALESCE(SUM(line_totals.total_cost), 0) AS "totalCost",
                COUNT(*) FILTER (WHERE COALESCE(d.metadata->>'qualityStatus', 'PENDING') = 'PASSED')::int AS "passedCount",
                COUNT(*) FILTER (WHERE COALESCE(d.metadata->>'qualityStatus', 'PENDING') = 'FAILED')::int AS "failedCount",
                COUNT(*) FILTER (WHERE jsonb_array_length(COALESCE(d.metadata->'discrepancies', '[]'::jsonb)) > 0)::int AS "discrepancyCount"
            FROM inventory_documents d
            LEFT JOIN LATERAL (
                SELECT
                    COALESCE(SUM(l.requested_quantity), 0)::int AS total_quantity,
                    COALESCE(SUM(COALESCE(l.unit_cost, 0) * l.requested_quantity), 0) AS total_cost
                FROM inventory_document_lines l
                WHERE l.document_id = d.id
            ) line_totals ON TRUE
            WHERE d.document_type = 'INBOUND'
            GROUP BY date_trunc('month', d.created_at)
            ORDER BY date_trunc('month', d.created_at) DESC
            LIMIT 12
            """
        )
    )
    daily_rows = await session.execute(
        text(
            """
            SELECT
                to_char(date_trunc('day', d.created_at), 'YYYY-MM-DD') AS period,
                COUNT(*)::int AS "receiptCount",
                COALESCE(SUM(line_totals.total_quantity), 0)::int AS "totalQuantity",
                COALESCE(SUM(line_totals.total_cost), 0) AS "totalCost",
                COUNT(*) FILTER (WHERE jsonb_array_length(COALESCE(d.metadata->'discrepancies', '[]'::jsonb)) > 0)::int AS "discrepancyCount"
            FROM inventory_documents d
            LEFT JOIN LATERAL (
                SELECT
                    COALESCE(SUM(l.requested_quantity), 0)::int AS total_quantity,
                    COALESCE(SUM(COALESCE(l.unit_cost, 0) * l.requested_quantity), 0) AS total_cost
                FROM inventory_document_lines l
                WHERE l.document_id = d.id
            ) line_totals ON TRUE
            WHERE d.document_type = 'INBOUND'
              AND d.created_at >= NOW() - INTERVAL '30 days'
            GROUP BY date_trunc('day', d.created_at)
            ORDER BY date_trunc('day', d.created_at) DESC
            LIMIT 30
            """
        )
    )
    supplier_rows = await session.execute(
        text(
            """
            SELECT
                COALESCE(NULLIF(d.supplier_name, ''), 'Không rõ') AS "supplierName",
                COUNT(*)::int AS "receiptCount",
                COALESCE(SUM(line_totals.total_quantity), 0)::int AS "totalQuantity",
                COALESCE(SUM(line_totals.total_cost), 0) AS "totalCost",
                COUNT(*) FILTER (WHERE jsonb_array_length(COALESCE(d.metadata->'discrepancies', '[]'::jsonb)) > 0)::int AS "discrepancyCount",
                COUNT(*) FILTER (WHERE COALESCE(d.metadata->>'qualityStatus', 'PENDING') = 'FAILED')::int AS "failedQualityCount",
                ROUND(
                    CASE WHEN COUNT(*) = 0 THEN 0
                         ELSE COUNT(*) FILTER (WHERE COALESCE(d.metadata->>'qualityStatus', 'PENDING') = 'FAILED')::numeric * 100 / COUNT(*)
                    END,
                    2
                ) AS "failureRate"
            FROM inventory_documents d
            LEFT JOIN LATERAL (
                SELECT
                    COALESCE(SUM(l.requested_quantity), 0)::int AS total_quantity,
                    COALESCE(SUM(COALESCE(l.unit_cost, 0) * l.requested_quantity), 0) AS total_cost
                FROM inventory_document_lines l
                WHERE l.document_id = d.id
            ) line_totals ON TRUE
            WHERE d.document_type = 'INBOUND'
            GROUP BY COALESCE(NULLIF(d.supplier_name, ''), 'Không rõ')
            ORDER BY COUNT(*) DESC, COALESCE(NULLIF(d.supplier_name, ''), 'Không rõ')
            LIMIT 50
            """
        )
    )
    return {
        "daily": [dict(row) for row in daily_rows.mappings().all()],
        "monthly": [dict(row) for row in monthly_rows.mappings().all()],
        "suppliers": [dict(row) for row in supplier_rows.mappings().all()],
    }


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
