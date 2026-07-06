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
                d.metadata->>'supplierId' AS "supplierId",
                d.metadata->>'invoiceNumber' AS "invoiceNumber",
                d.metadata->>'invoiceDate' AS "invoiceDate",
                COALESCE(d.metadata->>'paymentMode', 'DEBT') AS "paymentMode",
                COALESCE((d.metadata->>'paymentTermDays')::int, 0) AS "paymentTermDays",
                d.metadata->>'dueDate' AS "dueDate",
                COALESCE((d.metadata->>'paidAmount')::numeric, 0) AS "paidAmount",
                d.metadata->>'payableNote' AS "payableNote",
                COALESCE(d.metadata->'attachments', '[]'::jsonb) AS attachments,
                COALESCE(d.metadata->'pendingAttachments', '[]'::jsonb) AS "pendingAttachments",
                d.metadata->>'attachmentApprovalStatus' AS "attachmentApprovalStatus",
                d.metadata->>'attachmentApprovalNote' AS "attachmentApprovalNote",
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
                        'secondaryImeis', COALESCE(l.metadata->'secondaryImeis', '[]'::jsonb),
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
                        'tracksImei', COALESCE((l.metadata->>'tracksImei')::boolean, FALSE),
                        'tracksSerialNumber', COALESCE((l.metadata->>'tracksSerialNumber')::boolean, FALSE),
                        'imeis', COALESCE(l.metadata->'imeis', '[]'::jsonb),
                        'serialNumbers', COALESCE(l.metadata->'serialNumbers', '[]'::jsonb),
                        'missingImeis', COALESCE(l.metadata->'missingImeis', '[]'::jsonb),
                        'unexpectedImeis', COALESCE(l.metadata->'unexpectedImeis', '[]'::jsonb),
                        'missingSerialNumbers', COALESCE(l.metadata->'missingSerialNumbers', '[]'::jsonb),
                        'unexpectedSerialNumbers', COALESCE(l.metadata->'unexpectedSerialNumbers', '[]'::jsonb),
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


async def list_inventory_transfers(session: AsyncSession, search: str = "") -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                d.id::text AS id,
                d.document_no AS "referenceCode",
                d.status,
                d.reason,
                d.note,
                d.created_at AS "createdAt",
                d.created_by::text AS "createdBy",
                d.approved_at AS "approvedAt",
                d.approved_by::text AS "approvedBy",
                d.cancelled_at AS "cancelledAt",
                d.cancelled_by::text AS "cancelledBy",
                COUNT(l.id)::int AS "lineCount",
                COALESCE(SUM(COALESCE(l.requested_quantity, 0)), 0)::int AS "totalQuantity",
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
                        'quantity', COALESCE(l.requested_quantity, 0),
                        'fromLocationId', l.location_id::text,
                        'fromLocationCode', source.code,
                        'fromLocationName', source.name,
                        'toLocationId', l.metadata->>'toLocationId',
                        'toLocationCode', target.code,
                        'toLocationName', target.name,
                        'imeis', COALESCE(l.metadata->'imeis', '[]'::jsonb),
                        'serialNumbers', COALESCE(l.metadata->'serialNumbers', '[]'::jsonb),
                        'targetIdentifierStatus', l.metadata->>'targetIdentifierStatus',
                        'note', l.note
                    )
                    ORDER BY l.created_at, p.name, pv.sku
                ) AS lines
            FROM inventory_documents d
            JOIN inventory_document_lines l ON l.document_id = d.id
            JOIN products p ON p.id = l.product_id
            LEFT JOIN product_variants pv ON pv.id = l.variant_id
            LEFT JOIN inventory_locations source ON source.id = l.location_id
            LEFT JOIN inventory_locations target ON target.id = CAST(NULLIF(l.metadata->>'toLocationId', '') AS uuid)
            WHERE d.document_type = 'TRANSFER'
              AND (:search = ''
                OR LOWER(COALESCE(d.document_no, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.status, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.reason, '')) LIKE LOWER(:pattern)
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(p.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(source.code, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(target.code, '')) LIKE LOWER(:pattern)
              )
            GROUP BY d.id
            ORDER BY d.created_at DESC
            LIMIT 100
            """
        ),
        {"search": search, "pattern": f"%{search}%"},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_internal_holds(session: AsyncSession, search: str = "") -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                d.id::text AS id,
                d.document_no AS "referenceCode",
                d.status,
                d.reason,
                d.note,
                d.metadata->>'holdType' AS "holdType",
                d.created_at AS "createdAt",
                d.created_by::text AS "createdBy",
                d.approved_at AS "approvedAt",
                d.approved_by::text AS "approvedBy",
                d.posted_at AS "postedAt",
                d.posted_by::text AS "postedBy",
                d.cancelled_at AS "cancelledAt",
                d.cancelled_by::text AS "cancelledBy",
                COUNT(l.id)::int AS "lineCount",
                COALESCE(SUM(COALESCE(l.requested_quantity, 0)), 0)::int AS "totalQuantity",
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
                        'locationId', l.location_id::text,
                        'locationCode', loc.code,
                        'locationName', loc.name,
                        'quantity', COALESCE(l.requested_quantity, 0),
                        'holdType', COALESCE(l.metadata->>'holdType', d.metadata->>'holdType'),
                        'note', l.note
                    )
                    ORDER BY l.created_at, p.name, pv.sku
                ) AS lines
            FROM inventory_documents d
            JOIN inventory_document_lines l ON l.document_id = d.id
            JOIN products p ON p.id = l.product_id
            LEFT JOIN product_variants pv ON pv.id = l.variant_id
            LEFT JOIN inventory_locations loc ON loc.id = l.location_id
            WHERE d.document_type = 'INTERNAL_HOLD'
              AND (:search = ''
                OR LOWER(COALESCE(d.document_no, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.status, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.reason, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.metadata->>'holdType', '')) LIKE LOWER(:pattern)
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(p.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(loc.code, '')) LIKE LOWER(:pattern)
              )
            GROUP BY d.id
            ORDER BY d.created_at DESC
            LIMIT 100
            """
        ),
        {"search": search, "pattern": f"%{search}%"},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_disposals(session: AsyncSession, search: str = "") -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                d.id::text AS id,
                d.document_no AS "referenceCode",
                d.status,
                d.reason,
                d.note,
                d.metadata->>'dispositionType' AS "dispositionType",
                d.metadata->>'partnerName' AS "partnerName",
                d.metadata->>'recoveryValue' AS "recoveryValue",
                d.created_at AS "createdAt",
                d.created_by::text AS "createdBy",
                d.approved_at AS "approvedAt",
                d.approved_by::text AS "approvedBy",
                d.posted_at AS "postedAt",
                d.posted_by::text AS "postedBy",
                d.cancelled_at AS "cancelledAt",
                d.cancelled_by::text AS "cancelledBy",
                COUNT(l.id)::int AS "lineCount",
                COALESCE(SUM(COALESCE(l.requested_quantity, 0)), 0)::int AS "totalQuantity",
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
                        'locationId', l.location_id::text,
                        'locationCode', loc.code,
                        'locationName', loc.name,
                        'locationPurpose', loc.purpose,
                        'quantity', COALESCE(l.requested_quantity, 0),
                        'dispositionType', COALESCE(l.metadata->>'dispositionType', d.metadata->>'dispositionType'),
                        'imeis', COALESCE(l.metadata->'imeis', '[]'::jsonb),
                        'serialNumbers', COALESCE(l.metadata->'serialNumbers', '[]'::jsonb),
                        'note', l.note
                    )
                    ORDER BY l.created_at, p.name, pv.sku
                ) AS lines
            FROM inventory_documents d
            JOIN inventory_document_lines l ON l.document_id = d.id
            JOIN products p ON p.id = l.product_id
            LEFT JOIN product_variants pv ON pv.id = l.variant_id
            LEFT JOIN inventory_locations loc ON loc.id = l.location_id
            WHERE d.document_type = 'DISPOSAL'
              AND (:search = ''
                OR LOWER(COALESCE(d.document_no, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.status, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.reason, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.metadata->>'dispositionType', '')) LIKE LOWER(:pattern)
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(p.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(loc.code, '')) LIKE LOWER(:pattern)
              )
            GROUP BY d.id
            ORDER BY d.created_at DESC
            LIMIT 100
            """
        ),
        {"search": search, "pattern": f"%{search}%"},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_cost_adjustments(session: AsyncSession, search: str = "") -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                d.id::text AS id,
                d.document_no AS "referenceCode",
                d.status,
                d.reason,
                d.note,
                d.created_at AS "createdAt",
                d.created_by::text AS "createdBy",
                d.approved_at AS "approvedAt",
                d.approved_by::text AS "approvedBy",
                d.posted_at AS "postedAt",
                d.posted_by::text AS "postedBy",
                d.cancelled_at AS "cancelledAt",
                d.cancelled_by::text AS "cancelledBy",
                COUNT(l.id)::int AS "lineCount",
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
                        'locationId', l.location_id::text,
                        'locationCode', loc.code,
                        'locationName', loc.name,
                        'onHandQuantity', COALESCE(l.expected_quantity, 0),
                        'oldAverageUnitCost', COALESCE((l.metadata->>'oldAverageUnitCost')::numeric, 0),
                        'newAverageUnitCost', COALESCE(l.unit_cost, 0),
                        'lotCosts', COALESCE(l.metadata->'lotCosts', '[]'::jsonb),
                        'appliedLots', COALESCE(l.metadata->'appliedLots', '[]'::jsonb),
                        'note', l.note
                    )
                    ORDER BY l.created_at, p.name, pv.sku
                ) AS lines
            FROM inventory_documents d
            JOIN inventory_document_lines l ON l.document_id = d.id
            JOIN products p ON p.id = l.product_id
            LEFT JOIN product_variants pv ON pv.id = l.variant_id
            LEFT JOIN inventory_locations loc ON loc.id = l.location_id
            WHERE d.document_type = 'COST_ADJUSTMENT'
              AND (:search = ''
                OR LOWER(COALESCE(d.document_no, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.status, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.reason, '')) LIKE LOWER(:pattern)
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(p.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(loc.code, '')) LIKE LOWER(:pattern)
              )
            GROUP BY d.id
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


async def insert_inventory_transfer_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    reference_code: str,
    reason: str,
    note: str | None,
    created_by: UUID | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status,
                reference_code, reason, note, created_by
            )
            VALUES (
                :id, :document_no, 'TRANSFER', 'DRAFT',
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
            "created_by": created_by,
        },
    )


async def insert_inventory_internal_hold_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    reference_code: str,
    hold_type: str,
    reason: str,
    note: str | None,
    created_by: UUID | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status,
                reference_code, reason, note, metadata, created_by
            )
            VALUES (
                :id, :document_no, 'INTERNAL_HOLD', 'DRAFT',
                :reference_code, :reason, :note,
                jsonb_build_object('holdType', CAST(:hold_type AS TEXT)),
                :created_by
            )
            """
        ),
        {
            "id": document_id,
            "document_no": reference_code,
            "reference_code": reference_code,
            "hold_type": hold_type,
            "reason": reason,
            "note": note,
            "created_by": created_by,
        },
    )


async def insert_inventory_disposal_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    reference_code: str,
    disposition_type: str,
    reason: str,
    note: str | None,
    partner_name: str | None,
    recovery_value: float | None,
    created_by: UUID | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status,
                reference_code, reason, note, metadata, created_by
            )
            VALUES (
                :id, :document_no, 'DISPOSAL', 'DRAFT',
                :reference_code, :reason, :note,
                jsonb_build_object(
                    'dispositionType', CAST(:disposition_type AS TEXT),
                    'partnerName', CAST(:partner_name AS TEXT),
                    'recoveryValue', CAST(:recovery_value AS NUMERIC)
                ),
                :created_by
            )
            """
        ),
        {
            "id": document_id,
            "document_no": reference_code,
            "reference_code": reference_code,
            "disposition_type": disposition_type,
            "reason": reason,
            "note": note,
            "partner_name": partner_name,
            "recovery_value": recovery_value,
            "created_by": created_by,
        },
    )


async def insert_inventory_cost_adjustment_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    reference_code: str,
    reason: str,
    note: str | None,
    created_by: UUID | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status,
                reference_code, reason, note, created_by
            )
            VALUES (
                :id, :document_no, 'COST_ADJUSTMENT', 'DRAFT',
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
    metadata: dict,
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
                :variance_quantity, :note, CAST(:metadata AS jsonb)
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
            "metadata": json.dumps(metadata, ensure_ascii=False),
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


async def insert_inventory_transfer_line(
    session: AsyncSession,
    *,
    line_id: UUID,
    document_id: UUID,
    product_id: UUID,
    variant_id: UUID | None,
    from_location_id: UUID,
    to_location_id: UUID,
    quantity: int,
    imeis: list[str],
    serial_numbers: list[str],
    target_identifier_status: str,
    note: str | None,
) -> None:
    metadata = {
        "toLocationId": str(to_location_id),
        "imeis": imeis,
        "serialNumbers": serial_numbers,
        "targetIdentifierStatus": target_identifier_status,
    }
    await session.execute(
        text(
            """
            INSERT INTO inventory_document_lines (
                id, document_id, product_id, variant_id, location_id,
                requested_quantity, expected_quantity, counted_quantity,
                variance_quantity, note, metadata
            )
            VALUES (
                :id, :document_id, :product_id, :variant_id, :from_location_id,
                :quantity, 0, 0,
                0, :note, CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "id": line_id,
            "document_id": document_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "from_location_id": from_location_id,
            "quantity": quantity,
            "note": note,
            "metadata": json.dumps(metadata, ensure_ascii=False),
        },
    )


async def insert_inventory_internal_hold_line(
    session: AsyncSession,
    *,
    line_id: UUID,
    document_id: UUID,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    quantity: int,
    hold_type: str,
    reason: str,
    note: str | None,
    imeis: list[str] | None = None,
    serial_numbers: list[str] | None = None,
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
                :quantity, 0, 0,
                0, :note,
                CAST(:metadata AS jsonb)
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
            "note": note,
            "metadata": json.dumps(
                {
                    "holdType": hold_type,
                    "holdReason": reason,
                    "imeis": imeis or [],
                    "serialNumbers": serial_numbers or [],
                },
                ensure_ascii=False,
            ),
        },
    )


async def insert_inventory_disposal_line(
    session: AsyncSession,
    *,
    line_id: UUID,
    document_id: UUID,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    quantity: int,
    disposition_type: str,
    reason: str,
    imeis: list[str],
    serial_numbers: list[str],
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
                :quantity, 0, 0,
                0, :note,
                CAST(:metadata AS jsonb)
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
            "note": note,
            "metadata": json.dumps(
                {
                    "dispositionType": disposition_type,
                    "dispositionReason": reason,
                    "imeis": imeis,
                    "serialNumbers": serial_numbers,
                },
                ensure_ascii=False,
            ),
        },
    )


async def insert_inventory_cost_adjustment_line(
    session: AsyncSession,
    *,
    line_id: UUID,
    document_id: UUID,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    on_hand_quantity: int,
    old_average_unit_cost: float,
    new_average_unit_cost: float,
    lot_costs: list[dict],
    note: str | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_document_lines (
                id, document_id, product_id, variant_id, location_id,
                requested_quantity, expected_quantity, counted_quantity,
                variance_quantity, unit_cost, note, metadata
            )
            VALUES (
                :id, :document_id, :product_id, :variant_id, :location_id,
                0, :on_hand_quantity, :on_hand_quantity,
                0, :new_average_unit_cost, :note, CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "id": line_id,
            "document_id": document_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "on_hand_quantity": on_hand_quantity,
            "new_average_unit_cost": new_average_unit_cost,
            "note": note,
            "metadata": json.dumps(
                {
                    "oldAverageUnitCost": float(old_average_unit_cost or 0),
                    "newAverageUnitCost": float(new_average_unit_cost or 0),
                    "lotCosts": lot_costs,
                    "appliedLots": [],
                },
                ensure_ascii=False,
            ),
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
                    d.created_by,
                    d.target_location_id,
                    target.code AS "locationCode",
                    target.name AS "locationName"
                FROM inventory_documents d
                LEFT JOIN inventory_locations target ON target.id = d.target_location_id
                WHERE d.document_type = 'COUNT' AND d.document_no = :reference_code
                FOR UPDATE OF d
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
                    d.created_by,
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


async def get_inventory_transfer_for_update(session: AsyncSession, reference_code: str) -> dict | None:
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
                    d.created_by
                FROM inventory_documents d
                WHERE d.document_type = 'TRANSFER' AND d.document_no = :reference_code
                FOR UPDATE OF d
                """
            ),
            {"reference_code": reference_code},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_inventory_internal_hold_for_update(session: AsyncSession, reference_code: str) -> dict | None:
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
                    d.created_by,
                    d.metadata->>'holdType' AS "holdType"
                FROM inventory_documents d
                WHERE d.document_type = 'INTERNAL_HOLD' AND d.document_no = :reference_code
                FOR UPDATE OF d
                """
            ),
            {"reference_code": reference_code},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_inventory_disposal_for_update(session: AsyncSession, reference_code: str) -> dict | None:
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
                    d.created_by,
                    d.metadata->>'dispositionType' AS "dispositionType",
                    d.metadata->>'partnerName' AS "partnerName",
                    d.metadata->>'recoveryValue' AS "recoveryValue"
                FROM inventory_documents d
                WHERE d.document_type = 'DISPOSAL' AND d.document_no = :reference_code
                FOR UPDATE OF d
                """
            ),
            {"reference_code": reference_code},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_inventory_cost_adjustment_for_update(session: AsyncSession, reference_code: str) -> dict | None:
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
                    d.created_by
                FROM inventory_documents d
                WHERE d.document_type = 'COST_ADJUSTMENT' AND d.document_no = :reference_code
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
                COALESCE((l.metadata->>'tracksImei')::boolean, FALSE) AS "tracksImei",
                COALESCE((l.metadata->>'tracksSerialNumber')::boolean, FALSE) AS "tracksSerialNumber",
                COALESCE(l.metadata->'imeis', '[]'::jsonb) AS imeis,
                COALESCE(l.metadata->'serialNumbers', '[]'::jsonb) AS "serialNumbers",
                COALESCE(l.metadata->'missingImeis', '[]'::jsonb) AS "missingImeis",
                COALESCE(l.metadata->'unexpectedImeis', '[]'::jsonb) AS "unexpectedImeis",
                COALESCE(l.metadata->'missingSerialNumbers', '[]'::jsonb) AS "missingSerialNumbers",
                COALESCE(l.metadata->'unexpectedSerialNumbers', '[]'::jsonb) AS "unexpectedSerialNumbers",
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


async def list_inventory_transfer_lines(session: AsyncSession, document_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                l.id,
                l.product_id AS "productId",
                l.variant_id AS "variantId",
                l.location_id AS "fromLocationId",
                CAST(NULLIF(l.metadata->>'toLocationId', '') AS uuid) AS "toLocationId",
                COALESCE(l.requested_quantity, 0)::int AS quantity,
                COALESCE(l.metadata->'imeis', '[]'::jsonb) AS imeis,
                COALESCE(l.metadata->'serialNumbers', '[]'::jsonb) AS "serialNumbers",
                l.metadata->>'targetIdentifierStatus' AS "targetIdentifierStatus",
                l.note,
                source.code AS "fromLocationCode",
                source.name AS "fromLocationName",
                source.purpose AS "fromLocationPurpose",
                target.code AS "toLocationCode",
                target.name AS "toLocationName",
                target.purpose AS "toLocationPurpose"
            FROM inventory_document_lines l
            LEFT JOIN inventory_locations source ON source.id = l.location_id
            LEFT JOIN inventory_locations target ON target.id = CAST(NULLIF(l.metadata->>'toLocationId', '') AS uuid)
            WHERE l.document_id = :document_id
            ORDER BY l.created_at, l.id
            """
        ),
        {"document_id": document_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_internal_hold_lines(session: AsyncSession, document_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                l.id,
                l.product_id AS "productId",
                l.variant_id AS "variantId",
                l.location_id AS "locationId",
                COALESCE(l.requested_quantity, 0)::int AS quantity,
                COALESCE(l.metadata->>'holdType', d.metadata->>'holdType') AS "holdType",
                COALESCE(l.metadata->>'holdReason', d.reason) AS reason,
                COALESCE(l.metadata->'imeis', '[]'::jsonb) AS imeis,
                COALESCE(l.metadata->'serialNumbers', '[]'::jsonb) AS "serialNumbers",
                l.note,
                loc.code AS "locationCode",
                loc.name AS "locationName"
            FROM inventory_document_lines l
            JOIN inventory_documents d ON d.id = l.document_id
            LEFT JOIN inventory_locations loc ON loc.id = l.location_id
            WHERE l.document_id = :document_id
            ORDER BY l.created_at, l.id
            """
        ),
        {"document_id": document_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_disposal_lines(session: AsyncSession, document_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                l.id,
                l.product_id AS "productId",
                l.variant_id AS "variantId",
                l.location_id AS "locationId",
                COALESCE(l.requested_quantity, 0)::int AS quantity,
                COALESCE(l.metadata->>'dispositionType', d.metadata->>'dispositionType') AS "dispositionType",
                COALESCE(l.metadata->>'dispositionReason', d.reason) AS reason,
                COALESCE(l.metadata->'imeis', '[]'::jsonb) AS imeis,
                COALESCE(l.metadata->'serialNumbers', '[]'::jsonb) AS "serialNumbers",
                l.note,
                loc.code AS "locationCode",
                loc.name AS "locationName",
                loc.purpose AS "locationPurpose"
            FROM inventory_document_lines l
            JOIN inventory_documents d ON d.id = l.document_id
            LEFT JOIN inventory_locations loc ON loc.id = l.location_id
            WHERE l.document_id = :document_id
            ORDER BY l.created_at, l.id
            """
        ),
        {"document_id": document_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_cost_adjustment_lines(session: AsyncSession, document_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                l.id,
                l.product_id AS "productId",
                l.variant_id AS "variantId",
                l.location_id AS "locationId",
                COALESCE(l.expected_quantity, 0)::int AS "onHandQuantity",
                COALESCE((l.metadata->>'oldAverageUnitCost')::numeric, 0) AS "oldAverageUnitCost",
                COALESCE(l.unit_cost, 0) AS "newAverageUnitCost",
                COALESCE(l.metadata->'lotCosts', '[]'::jsonb) AS "lotCosts",
                COALESCE(l.metadata->'appliedLots', '[]'::jsonb) AS "appliedLots",
                l.note
            FROM inventory_document_lines l
            WHERE l.document_id = :document_id
            ORDER BY l.created_at, l.id
            """
        ),
        {"document_id": document_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def get_inventory_level_for_transfer(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    il.id,
                    il.on_hand_quantity::int AS "onHandQuantity",
                    il.reserved_quantity::int AS "reservedQuantity",
                    il.average_unit_cost AS "averageUnitCost"
                FROM inventory_levels il
                WHERE il.location_id = :location_id
                  AND (
                        (CAST(:variant_id AS uuid) IS NULL AND il.product_id = :product_id AND il.variant_id IS NULL)
                     OR (CAST(:variant_id AS uuid) IS NOT NULL AND il.product_id IS NULL AND il.variant_id = CAST(:variant_id AS uuid))
                  )
                FOR UPDATE OF il
                """
            ),
            {"product_id": product_id, "variant_id": variant_id, "location_id": location_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def decrement_inventory_level_quantity(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    quantity: int,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                UPDATE inventory_levels
                SET on_hand_quantity = on_hand_quantity - :quantity,
                    updated_at = NOW()
                WHERE location_id = :location_id
                  AND (
                        (CAST(:variant_id AS uuid) IS NULL AND product_id = :product_id AND variant_id IS NULL)
                     OR (CAST(:variant_id AS uuid) IS NOT NULL AND product_id IS NULL AND variant_id = CAST(:variant_id AS uuid))
                  )
                  AND on_hand_quantity - reserved_quantity >= :quantity
                RETURNING
                    on_hand_quantity::int AS "onHandQuantity",
                    reserved_quantity::int AS "reservedQuantity",
                    average_unit_cost AS "averageUnitCost"
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "location_id": location_id,
                "quantity": quantity,
            },
        )
    ).mappings().first()
    return dict(row) if row else None


async def adjust_inventory_level_reserved_quantity(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    delta: int,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                UPDATE inventory_levels
                SET reserved_quantity = reserved_quantity + :delta,
                    updated_at = NOW()
                WHERE location_id = :location_id
                  AND (
                        (CAST(:variant_id AS uuid) IS NULL AND product_id = :product_id AND variant_id IS NULL)
                     OR (CAST(:variant_id AS uuid) IS NOT NULL AND product_id IS NULL AND variant_id = CAST(:variant_id AS uuid))
                  )
                  AND reserved_quantity + :delta >= 0
                  AND reserved_quantity + :delta <= on_hand_quantity
                RETURNING
                    on_hand_quantity::int AS "onHandQuantity",
                    reserved_quantity::int AS "reservedQuantity"
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "location_id": location_id,
                "delta": delta,
            },
        )
    ).mappings().first()
    return dict(row) if row else None


async def list_active_lots_for_cost_adjustment(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id,
                lot_code AS "lotCode",
                remaining_quantity AS "remainingQuantity",
                unit_cost AS "unitCost"
            FROM inventory_lots
            WHERE (
                    (CAST(:variant_id AS uuid) IS NULL AND product_id = :product_id AND variant_id IS NULL)
                 OR (CAST(:variant_id AS uuid) IS NOT NULL AND variant_id = CAST(:variant_id AS uuid))
              )
              AND location_id = :location_id
              AND status = 'ACTIVE'
              AND remaining_quantity > 0
            ORDER BY received_at ASC, created_at ASC, lot_code ASC
            FOR UPDATE
            """
        ),
        {"product_id": product_id, "variant_id": variant_id, "location_id": location_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def update_inventory_level_average_unit_cost(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    new_average_unit_cost: float,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                UPDATE inventory_levels
                SET average_unit_cost = CAST(:new_average_unit_cost AS NUMERIC),
                    updated_at = NOW()
                WHERE location_id = :location_id
                  AND (
                        (CAST(:variant_id AS uuid) IS NULL AND product_id = :product_id AND variant_id IS NULL)
                     OR (CAST(:variant_id AS uuid) IS NOT NULL AND product_id IS NULL AND variant_id = CAST(:variant_id AS uuid))
                  )
                RETURNING
                    on_hand_quantity::int AS "onHandQuantity",
                    reserved_quantity::int AS "reservedQuantity",
                    average_unit_cost AS "averageUnitCost"
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "location_id": location_id,
                "new_average_unit_cost": new_average_unit_cost,
            },
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_inventory_lot_unit_cost(
    session: AsyncSession,
    *,
    lot_id: UUID,
    new_unit_cost: float,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                UPDATE inventory_lots
                SET unit_cost = CAST(:new_unit_cost AS NUMERIC),
                    updated_at = NOW()
                WHERE id = :lot_id
                RETURNING
                    id,
                    lot_code AS "lotCode",
                    remaining_quantity AS "remainingQuantity",
                    unit_cost AS "unitCost"
                """
            ),
            {"lot_id": lot_id, "new_unit_cost": new_unit_cost},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_inventory_cost_adjustment_line_applied_lots(
    session: AsyncSession,
    *,
    line_id: UUID,
    applied_lots: list[dict],
) -> None:
    await session.execute(
        text(
            """
            UPDATE inventory_document_lines
            SET metadata = jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{appliedLots}',
                    CAST(:applied_lots AS jsonb),
                    TRUE
                )
            WHERE id = :line_id
            """
        ),
        {"line_id": line_id, "applied_lots": json.dumps(applied_lots, ensure_ascii=False)},
    )


async def transfer_inventory_level_quantity(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    from_location_id: UUID,
    to_location_id: UUID,
    quantity: int,
    average_unit_cost,
) -> None:
    if variant_id:
        await session.execute(
            text(
                """
                UPDATE inventory_levels
                SET on_hand_quantity = on_hand_quantity - :quantity,
                    updated_at = NOW()
                WHERE product_id IS NULL
                  AND variant_id = :variant_id
                  AND location_id = :from_location_id
                """
            ),
            {"variant_id": variant_id, "from_location_id": from_location_id, "quantity": quantity},
        )
        await session.execute(
            text(
                """
                WITH updated AS (
                    UPDATE inventory_levels
                    SET on_hand_quantity = on_hand_quantity + :quantity,
                        average_unit_cost = CASE
                            WHEN COALESCE(average_unit_cost, 0) = 0 THEN COALESCE(CAST(:average_unit_cost AS NUMERIC), 0)
                            ELSE average_unit_cost
                        END,
                        updated_at = NOW()
                    WHERE product_id IS NULL
                      AND variant_id = :variant_id
                      AND location_id = :to_location_id
                    RETURNING id
                )
                INSERT INTO inventory_levels (
                    id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost
                )
                SELECT gen_random_uuid(), NULL, :variant_id, :to_location_id, :quantity, 0, COALESCE(CAST(:average_unit_cost AS NUMERIC), 0)
                WHERE NOT EXISTS (SELECT 1 FROM updated)
                """
            ),
            {"variant_id": variant_id, "to_location_id": to_location_id, "quantity": quantity, "average_unit_cost": average_unit_cost},
        )
        return

    await session.execute(
        text(
            """
            UPDATE inventory_levels
            SET on_hand_quantity = on_hand_quantity - :quantity,
                updated_at = NOW()
            WHERE product_id = :product_id
              AND variant_id IS NULL
              AND location_id = :from_location_id
            """
        ),
        {"product_id": product_id, "from_location_id": from_location_id, "quantity": quantity},
    )
    await session.execute(
        text(
            """
            WITH updated AS (
                UPDATE inventory_levels
                SET on_hand_quantity = on_hand_quantity + :quantity,
                    average_unit_cost = CASE
                        WHEN COALESCE(average_unit_cost, 0) = 0 THEN COALESCE(CAST(:average_unit_cost AS NUMERIC), 0)
                        ELSE average_unit_cost
                    END,
                    updated_at = NOW()
                WHERE product_id = :product_id
                  AND variant_id IS NULL
                  AND location_id = :to_location_id
                RETURNING id
            )
            INSERT INTO inventory_levels (
                id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost
            )
            SELECT gen_random_uuid(), :product_id, NULL, :to_location_id, :quantity, 0, COALESCE(CAST(:average_unit_cost AS NUMERIC), 0)
            WHERE NOT EXISTS (SELECT 1 FROM updated)
            """
        ),
        {"product_id": product_id, "to_location_id": to_location_id, "quantity": quantity, "average_unit_cost": average_unit_cost},
    )


async def move_product_imeis_location(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    from_location_id: UUID,
    to_location_id: UUID,
    imeis: list[str],
    target_status: str = "IN_STOCK",
) -> list[str]:
    if not imeis:
        return []
    result = await session.execute(
        text(
            """
            WITH paired_imeis AS (
                SELECT pair.imei1 AS imei
                FROM product_identifier_pairs pair
                WHERE pair.product_id = :product_id
                  AND pair.variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
                  AND (pair.imei1 = ANY(:imeis) OR pair.imei2 = ANY(:imeis))
                UNION
                SELECT pair.imei2 AS imei
                FROM product_identifier_pairs pair
                WHERE pair.product_id = :product_id
                  AND pair.variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
                  AND pair.imei2 IS NOT NULL
                  AND (pair.imei1 = ANY(:imeis) OR pair.imei2 = ANY(:imeis))
            ),
            target_imeis AS (
                SELECT UNNEST(:imeis) AS imei
                UNION
                SELECT imei FROM paired_imeis
            )
            UPDATE product_imeis
            SET location_id = :to_location_id,
                status = :target_status,
                updated_at = NOW()
            WHERE product_id = :product_id
              AND (
                    (CAST(:variant_id AS uuid) IS NULL AND variant_id IS NULL)
                 OR (CAST(:variant_id AS uuid) IS NOT NULL AND variant_id = CAST(:variant_id AS uuid))
              )
              AND location_id = :from_location_id
              AND status IN (
                    'IN_STOCK', 'RETURNED', 'WARRANTY', 'IN_WARRANTY',
                    'DEFECTIVE_RETURNED', 'INSPECTION_PENDING'
              )
              AND imei IN (SELECT imei FROM target_imeis)
            RETURNING imei
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "from_location_id": from_location_id,
            "to_location_id": to_location_id,
            "target_status": target_status,
            "imeis": imeis,
        },
    )
    return [str(row["imei"]) for row in result.mappings().all()]


async def move_product_serial_numbers_location(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    from_location_id: UUID,
    to_location_id: UUID,
    serial_numbers: list[str],
    target_status: str = "IN_STOCK",
) -> list[str]:
    if not serial_numbers:
        return []
    result = await session.execute(
        text(
            """
            UPDATE product_serial_numbers
            SET location_id = :to_location_id,
                status = :target_status,
                updated_at = NOW()
            WHERE product_id = :product_id
              AND (
                    (CAST(:variant_id AS uuid) IS NULL AND variant_id IS NULL)
                 OR (CAST(:variant_id AS uuid) IS NOT NULL AND variant_id = CAST(:variant_id AS uuid))
              )
              AND location_id = :from_location_id
              AND status IN (
                    'IN_STOCK', 'RETURNED', 'WARRANTY', 'IN_WARRANTY',
                    'DEFECTIVE_RETURNED', 'INSPECTION_PENDING'
              )
              AND serial_number = ANY(:serial_numbers)
            RETURNING serial_number
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "from_location_id": from_location_id,
            "to_location_id": to_location_id,
            "target_status": target_status,
            "serial_numbers": serial_numbers,
        },
    )
    return [str(row["serial_number"]) for row in result.mappings().all()]


async def dispose_product_imeis(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    imeis: list[str],
    target_status: str,
) -> list[str]:
    if not imeis:
        return []
    result = await session.execute(
        text(
            """
            WITH paired_imeis AS (
                SELECT pair.imei1 AS imei
                FROM product_identifier_pairs pair
                WHERE pair.product_id = :product_id
                  AND pair.variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
                  AND (pair.imei1 = ANY(:imeis) OR pair.imei2 = ANY(:imeis))
                UNION
                SELECT pair.imei2 AS imei
                FROM product_identifier_pairs pair
                WHERE pair.product_id = :product_id
                  AND pair.variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
                  AND pair.imei2 IS NOT NULL
                  AND (pair.imei1 = ANY(:imeis) OR pair.imei2 = ANY(:imeis))
            ),
            target_imeis AS (
                SELECT UNNEST(:imeis) AS imei
                UNION
                SELECT imei FROM paired_imeis
            )
            UPDATE product_imeis
            SET location_id = NULL,
                status = :target_status,
                updated_at = NOW()
            WHERE product_id = :product_id
              AND (
                    (CAST(:variant_id AS uuid) IS NULL AND variant_id IS NULL)
                 OR (CAST(:variant_id AS uuid) IS NOT NULL AND variant_id = CAST(:variant_id AS uuid))
              )
              AND location_id = :location_id
              AND status IN (
                    'IN_STOCK', 'RETURNED', 'WARRANTY', 'IN_WARRANTY',
                    'DEFECTIVE_RETURNED', 'INSPECTION_PENDING'
              )
              AND imei IN (SELECT imei FROM target_imeis)
            RETURNING imei
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "target_status": target_status,
            "imeis": imeis,
        },
    )
    return [str(row["imei"]) for row in result.mappings().all()]


async def dispose_product_serial_numbers(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    serial_numbers: list[str],
    target_status: str,
) -> list[str]:
    if not serial_numbers:
        return []
    result = await session.execute(
        text(
            """
            UPDATE product_serial_numbers
            SET location_id = NULL,
                status = :target_status,
                updated_at = NOW()
            WHERE product_id = :product_id
              AND (
                    (CAST(:variant_id AS uuid) IS NULL AND variant_id IS NULL)
                 OR (CAST(:variant_id AS uuid) IS NOT NULL AND variant_id = CAST(:variant_id AS uuid))
              )
              AND location_id = :location_id
              AND status IN (
                    'IN_STOCK', 'RETURNED', 'WARRANTY', 'IN_WARRANTY',
                    'DEFECTIVE_RETURNED', 'INSPECTION_PENDING'
              )
              AND serial_number = ANY(:serial_numbers)
            RETURNING serial_number
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "target_status": target_status,
            "serial_numbers": serial_numbers,
        },
    )
    return [str(row["serial_number"]) for row in result.mappings().all()]


async def list_products_due_for_cycle_count(
    session: AsyncSession,
    *,
    due_only: bool = False,
    search: str = "",
) -> list[dict]:
    query_str = """
        WITH last_counts AS (
            SELECT
                l.product_id,
                MAX(d.posted_at) AS last_counted_at
            FROM inventory_documents d
            JOIN inventory_document_lines l ON l.document_id = d.id
            WHERE d.document_type = 'COUNT' AND d.status = 'COMPLETED'
            GROUP BY l.product_id
        ),
        candidates AS (
            SELECT
                p.id::text AS "productId",
                p.sku,
                p.name,
                COALESCE((p.sales_config->>'cycleCountDays')::int, 30) AS "cycleCountDays",
                lc.last_counted_at AS "lastCountedAt",
                COALESCE(lc.last_counted_at, p.created_at) AS "baselineDate",
                EXTRACT(DAY FROM (NOW() - COALESCE(lc.last_counted_at, p.created_at)))::int AS "daysSinceLastCount"
            FROM products p
            LEFT JOIN last_counts lc ON lc.product_id = p.id
            WHERE p.status = 'ACTIVE'
        )
        SELECT
            c."productId",
            c.sku,
            c.name,
            c."cycleCountDays",
            c."lastCountedAt",
            c."daysSinceLastCount",
            (c."baselineDate" + (c."cycleCountDays" * '1 day'::interval)) AS "nextCountDueDate",
            (c."daysSinceLastCount" >= c."cycleCountDays")::boolean AS "isDue"
        FROM candidates c
        WHERE 1=1
    """
    params = {}
    if due_only:
        query_str += ' AND (c."daysSinceLastCount" >= c."cycleCountDays")'
    if search:
        query_str += " AND (c.sku ILIKE :search OR c.name ILIKE :search)"
        params["search"] = f"%{search}%"

    query_str += ' ORDER BY "isDue" DESC, c."daysSinceLastCount" DESC, c.sku ASC'

    res = await session.execute(text(query_str), params)
    return [dict(row) for row in res.mappings().all()]
