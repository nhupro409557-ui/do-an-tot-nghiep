import json
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_locations_containing_sku(
    session: AsyncSession,
    product_id: UUID,
    variant_id: UUID | None = None,
) -> list[str]:
    # Lấy danh sách location_id của inventory_levels có on_hand_quantity > 0 cho SKU này
    sql = """
        SELECT DISTINCT location_id::text
        FROM inventory_levels
        WHERE on_hand_quantity > 0
          AND (CAST(:variant_id AS uuid) IS NULL OR variant_id = CAST(:variant_id AS uuid))
          AND (CAST(:variant_id AS uuid) IS NOT NULL OR product_id = CAST(:product_id AS uuid))
    """
    params = {
        "product_id": product_id,
        "variant_id": variant_id,
    }
    result = await session.execute(text(sql), params)
    return [row[0] for row in result.all()]


async def list_level_issue_candidates(
    session: AsyncSession,
    product_id: UUID,
    variant_id: UUID | None = None,
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                il.location_id AS "locationId",
                loc.code AS "locationCode",
                loc.name AS "locationName",
                il.on_hand_quantity::int AS "onHandQuantity",
                il.reserved_quantity::int AS "reservedQuantity",
                GREATEST(il.on_hand_quantity - il.reserved_quantity, 0)::int AS "availableQuantity",
                il.updated_at AS "updatedAt",
                (
                    SELECT MIN(lot.received_at)
                    FROM inventory_lots lot
                    WHERE lot.product_id = :product_id
                      AND lot.variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
                      AND lot.location_id = il.location_id
                      AND lot.status = 'ACTIVE'
                      AND lot.remaining_quantity > 0
                ) AS "oldestReceivedAt"
            FROM inventory_levels il
            JOIN inventory_locations loc ON loc.id = il.location_id
            WHERE (
                    (CAST(:variant_id AS uuid) IS NULL AND il.product_id = :product_id AND il.variant_id IS NULL)
                 OR (CAST(:variant_id AS uuid) IS NOT NULL AND il.variant_id = CAST(:variant_id AS uuid))
              )
              AND GREATEST(il.on_hand_quantity - il.reserved_quantity, 0) > 0
              AND COALESCE(loc.status, 'ACTIVE') = 'ACTIVE'
            ORDER BY "oldestReceivedAt" ASC NULLS LAST, il.updated_at ASC, loc.code ASC
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
        },
    )
    return [dict(row) for row in result.mappings().all()]


async def list_inventory_outbound_documents(
    session: AsyncSession,
    *,
    search: str = "",
    status: str = "",
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                d.id::text AS id,
                d.document_no AS "referenceCode",
                d.document_no AS "document_no",
                d.status,
                d.reason AS "receiptReasonCode",
                o.order_code AS "orderCode",
                o.recipient_name AS "recipientName",
                o.recipient_phone AS "recipientPhone",
                source.code AS "locationCode",
                source.name AS "locationName",
                d.note,
                d.created_at AS "createdAt",
                d.created_at AS "created_at",
                d.created_by::text AS "createdBy",
                d.created_by::text AS "created_by",
                MAX(COALESCE(NULLIF(created_user.full_name, ''), created_user.email)) AS "createdByName",
                d.approved_at AS "approvedAt",
                d.approved_by::text AS "approvedBy",
                MAX(COALESCE(NULLIF(approved_user.full_name, ''), approved_user.email)) AS "approvedByName",
                d.posted_at AS "postedAt",
                d.posted_by::text AS "postedBy",
                MAX(COALESCE(NULLIF(posted_user.full_name, ''), posted_user.email)) AS "postedByName",
                d.cancelled_at AS "cancelledAt",
                d.cancelled_by::text AS "cancelledBy",
                MAX(COALESCE(NULLIF(cancelled_user.full_name, ''), cancelled_user.email)) AS "cancelledByName",
                COUNT(l.id)::int AS "lineCount",
                COALESCE(SUM(l.requested_quantity), 0)::int AS "totalQuantity",
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
                        'approvedQuantity', COALESCE(l.approved_quantity, 0),
                        'tracksImei', COALESCE((l.metadata->>'tracksImei')::boolean, FALSE),
                        'tracksSerialNumber', COALESCE((l.metadata->>'tracksSerialNumber')::boolean, FALSE),
                        'imeis', COALESCE(l.metadata->'imeis', '[]'::jsonb),
                        'serialNumbers', COALESCE(l.metadata->'serialNumbers', '[]'::jsonb),
                        'imeiCount', jsonb_array_length(COALESCE(l.metadata->'imeis', '[]'::jsonb)),
                        'serialNumberCount', jsonb_array_length(COALESCE(l.metadata->'serialNumbers', '[]'::jsonb)),
                        'storageLocationCode', l.metadata->>'storageLocationCode',
                        'storageLocationName', l.metadata->>'storageLocationName',
                        'locationId', l.location_id::text,
                        'unitCost', l.unit_cost,
                        'note', l.note
                    )
                    ORDER BY l.created_at, p.name, pv.sku
                ) AS lines
            FROM inventory_documents d
            LEFT JOIN inventory_document_lines l ON l.document_id = d.id
            LEFT JOIN products p ON p.id = l.product_id
            LEFT JOIN product_variants pv ON pv.id = l.variant_id
            LEFT JOIN inventory_locations source ON source.id = d.source_location_id
            LEFT JOIN orders o ON o.id = d.order_id
            LEFT JOIN users created_user ON created_user.id = d.created_by
            LEFT JOIN users approved_user ON approved_user.id = d.approved_by
            LEFT JOIN users posted_user ON posted_user.id = d.posted_by
            LEFT JOIN users cancelled_user ON cancelled_user.id = d.cancelled_by
            WHERE d.document_type = 'OUTBOUND'
              AND (p.id IS NULL OR (p.deleted_at IS NULL AND p.status <> 'MERGED'))
              AND (:status = '' OR d.status = :status)
              AND (:date_from = '' OR d.created_at >= CAST(NULLIF(:date_from, '') AS date))
              AND (:date_to = '' OR d.created_at < CAST(NULLIF(:date_to, '') AS date) + INTERVAL '1 day')
              AND (:search = ''
                OR LOWER(COALESCE(d.document_no, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(o.order_code, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(o.recipient_name, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(o.recipient_phone, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(d.status, '')) LIKE LOWER(:pattern)
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(p.sku, '')) LIKE LOWER(:pattern)
                OR LOWER(COALESCE(pv.sku, '')) LIKE LOWER(:pattern)
              )
            GROUP BY d.id, source.code, source.name, o.order_code, o.recipient_name, o.recipient_phone
            ORDER BY d.created_at DESC
            """
        ),
        {
            "search": search,
            "pattern": f"%{search}%",
            "status": status,
            "date_from": date_from,
            "date_to": date_to,
        },
    )
    return [dict(row) for row in result.mappings().all()]


async def get_inventory_outbound_document(session: AsyncSession, document_no: str) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT
                d.id,
                d.document_no,
                d.status,
                d.reason,
                d.note,
                d.source_location_id,
                d.order_id,
                d.created_at,
                d.created_by,
                d.approved_at,
                d.approved_by,
                d.posted_at,
                d.posted_by,
                COALESCE(d.metadata, '{}'::jsonb) AS metadata,
                source.code AS "locationCode",
                source.name AS "locationName",
                o.order_code AS "orderCode",
                o.recipient_name AS "recipientName",
                o.recipient_phone AS "recipientPhone",
                o.shipping_address AS "shippingAddress"
            FROM inventory_documents d
            LEFT JOIN inventory_locations source ON source.id = d.source_location_id
            LEFT JOIN orders o ON o.id = d.order_id
            WHERE d.document_no = :document_no AND d.document_type = 'OUTBOUND'
            """
        ),
        {"document_no": document_no},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def list_inventory_outbound_lines(session: AsyncSession, document_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                l.id,
                l.product_id AS "productId",
                l.variant_id AS "variantId",
                l.location_id AS "locationId",
                l.requested_quantity AS quantity,
                l.approved_quantity AS "approvedQuantity",
                l.unit_cost AS "unitCost",
                l.note,
                p.name AS "productName",
                p.sku AS "productSku",
                pv.sku AS "variantSku",
                pv.color_name AS "variantColor",
                pv.configuration AS "variantConfiguration",
                COALESCE(l.metadata->'imeis', '[]'::jsonb) AS imeis,
                COALESCE(l.metadata->'serialNumbers', '[]'::jsonb) AS "serialNumbers",
                COALESCE((l.metadata->>'tracksImei')::boolean, FALSE) AS "tracksImei",
                COALESCE((l.metadata->>'tracksSerialNumber')::boolean, FALSE) AS "tracksSerialNumber",
                COALESCE(l.metadata->'allocations', '[]'::jsonb) AS allocations,
                loc.code AS "locationCode",
                loc.name AS "locationName"
            FROM inventory_document_lines l
            JOIN products p ON p.id = l.product_id
            LEFT JOIN product_variants pv ON pv.id = l.variant_id
            LEFT JOIN inventory_locations loc ON loc.id = l.location_id
            WHERE l.document_id = :document_id
            ORDER BY l.created_at, l.id
            """
        ),
        {"document_id": document_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def insert_inventory_outbound_document(
    session: AsyncSession,
    *,
    document_id: UUID,
    document_no: str,
    status: str,
    reason: str,
    note: str | None,
    source_location_id: UUID | None,
    order_id: UUID,
    created_by: UUID | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status, source_location_id,
                order_id, reason, note, created_by
            )
            VALUES (
                :id, :document_no, 'OUTBOUND', :status, :source_location_id,
                :order_id, :reason, :note, :created_by
            )
            """
        ),
        {
            "id": document_id,
            "document_no": document_no,
            "status": status,
            "source_location_id": source_location_id,
            "order_id": order_id,
            "reason": reason,
            "note": note,
            "created_by": created_by,
        },
    )


async def insert_inventory_outbound_line(
    session: AsyncSession,
    *,
    line_id: UUID,
    document_id: UUID,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID | None,
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
                requested_quantity, expected_quantity, approved_quantity, unit_cost, note, metadata
            )
            VALUES (
                :id, :document_id, :product_id, :variant_id, :location_id,
                :quantity, :quantity, :quantity, :unit_cost, :note, CAST(:metadata AS jsonb)
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
                },
                ensure_ascii=False,
            ),
        },
    )


async def update_inventory_outbound_status(
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
            SET status = :status\:\:varchar,
                note = COALESCE(:note, note),
                approved_at = CASE WHEN :status\:\:varchar = 'COMPLETED' THEN NOW() ELSE approved_at END,
                approved_by = CASE WHEN :status\:\:varchar = 'COMPLETED' THEN :actor_id ELSE approved_by END,
                posted_at = CASE WHEN :status\:\:varchar = 'COMPLETED' THEN NOW() ELSE posted_at END,
                posted_by = CASE WHEN :status\:\:varchar = 'COMPLETED' THEN :actor_id ELSE posted_by END
            WHERE id = :document_id
            """
        ),
        {
            "document_id": document_id,
            "status": status,
            "note": note,
            "actor_id": actor_id,
        },
    )


async def update_inventory_outbound_line(
    session: AsyncSession,
    *,
    line_id: UUID,
    location_id: UUID | None,
    approved_quantity: int,
    imeis: list[str],
    serial_numbers: list[str],
    storage_location_code: str | None = None,
    storage_location_name: str | None = None,
    allocations: list[dict] | None = None,
) -> None:
    # Lấy metadata cũ để cập nhật
    result = await session.execute(
        text("SELECT metadata FROM inventory_document_lines WHERE id = :line_id"),
        {"line_id": line_id},
    )
    row = result.first()
    metadata = dict(row[0]) if row and row[0] else {}

    metadata["imeis"] = imeis
    metadata["serialNumbers"] = serial_numbers
    metadata["storageLocationCode"] = storage_location_code
    metadata["storageLocationName"] = storage_location_name
    if allocations is not None:
        metadata["allocations"] = allocations

    await session.execute(
        text(
            """
            UPDATE inventory_document_lines
            SET location_id = :location_id,
                approved_quantity = :approved_quantity,
                metadata = CAST(:metadata AS jsonb)
            WHERE id = :line_id
            """
        ),
        {
            "line_id": line_id,
            "location_id": location_id,
            "approved_quantity": approved_quantity,
            "metadata": json.dumps(metadata, ensure_ascii=False),
        },
    )


async def get_inventory_level(
    session: AsyncSession,
    product_id: UUID | None,
    variant_id: UUID | None,
    location_id: UUID,
) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT on_hand_quantity, reserved_quantity, average_unit_cost
            FROM inventory_levels
            WHERE location_id = :location_id
              AND (
                (CAST(:variant_id AS uuid) IS NULL AND product_id = :product_id AND variant_id IS NULL)
                OR (CAST(:variant_id AS uuid) IS NOT NULL AND variant_id = :variant_id AND product_id IS NULL)
              )
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
        },
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def list_imei_statuses_by_location(
    session: AsyncSession,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    imeis: list[str],
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id, imei, status
            FROM product_imeis
            WHERE product_id = :product_id
              AND (
                (CAST(:variant_id AS uuid) IS NULL AND variant_id IS NULL)
                OR (CAST(:variant_id AS uuid) IS NOT NULL AND variant_id = :variant_id)
              )
              AND location_id = :location_id
              AND imei = ANY(:imeis)
              AND status = 'IN_STOCK'
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "imeis": imeis,
        },
    )
    return [dict(row) for row in result.mappings().all()]


async def list_serial_statuses_by_location(
    session: AsyncSession,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    serial_numbers: list[str],
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id, serial_number, status
            FROM product_serial_numbers
            WHERE product_id = :product_id
              AND (
                (CAST(:variant_id AS uuid) IS NULL AND variant_id IS NULL)
                OR (CAST(:variant_id AS uuid) IS NOT NULL AND variant_id = :variant_id)
              )
              AND location_id = :location_id
              AND serial_number = ANY(:serial_numbers)
              AND status = 'IN_STOCK'
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "serial_numbers": serial_numbers,
        },
    )
    return [dict(row) for row in result.mappings().all()]
