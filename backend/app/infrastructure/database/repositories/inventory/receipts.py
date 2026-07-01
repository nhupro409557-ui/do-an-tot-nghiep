import json
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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
                    COALESCE(d.metadata, '{}'::jsonb) AS metadata,
                    COALESCE(d.metadata->>'qualityStatus', 'PENDING') AS "qualityStatus",
                    COALESCE((d.metadata->>'quarantine')::boolean, FALSE) AS quarantine,
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
    metadata: dict | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status, target_location_id,
                supplier_name, reference_code, reason, note, created_by, metadata
            )
            VALUES (
                :id, :document_no, 'INBOUND', :status, :target_location_id,
                :supplier_name, :reference_code, :reason, :note, :created_by, CAST(:metadata AS jsonb)
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
            "metadata": json.dumps(metadata or {}, ensure_ascii=False),
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
    metadata: dict | None = None,
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
                metadata = CAST(:metadata AS jsonb),
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
            "metadata": json.dumps(metadata or {}, ensure_ascii=False),
        },
    )


async def update_inventory_receipt_quality(
    session: AsyncSession,
    *,
    document_id: UUID,
    quality_status: str,
    quality_note: str | None,
    quarantine: bool,
    quarantine_location: str | None,
) -> None:
    await session.execute(
        text(
            """
            UPDATE inventory_documents
            SET metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object(
                    'qualityStatus', CAST(:quality_status AS text),
                    'qualityLabel', CAST(:quality_label AS text),
                    'qualityNote', CAST(:quality_note AS text),
                    'quarantine', CAST(:quarantine AS boolean),
                    'quarantineLocation', CAST(:quarantine_location AS text)
                )
            WHERE id = :document_id
            """
        ),
        {
            "document_id": document_id,
            "quality_status": quality_status,
            "quality_label": {"PENDING": "Chờ kiểm tra", "PASSED": "Đạt", "FAILED": "Không đạt"}.get(quality_status, quality_status),
            "quality_note": quality_note,
            "quarantine": quarantine,
            "quarantine_location": quarantine_location,
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
    storage_location_code: str | None = None,
    storage_location_name: str | None = None,
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
                    "storageLocationCode": storage_location_code,
                    "storageLocationName": storage_location_name,
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
                l.location_id AS "locationId",
                l.requested_quantity AS quantity,
                l.unit_cost AS "unitCost",
                l.note,
                COALESCE(l.metadata->'imeis', '[]'::jsonb) AS imeis,
                COALESCE(l.metadata->'serialNumbers', '[]'::jsonb) AS "serialNumbers",
                COALESCE((l.metadata->>'tracksImei')::boolean, FALSE) AS "tracksImei",
                COALESCE((l.metadata->>'tracksSerialNumber')::boolean, FALSE) AS "tracksSerialNumber",
                COALESCE((l.metadata->>'receivedQuantity')::int, 0) AS "receivedQuantity",
                l.metadata->>'shortageReason' AS "shortageReason",
                l.metadata->>'storageLocationCode' AS "storageLocationCode",
                l.metadata->>'storageLocationName' AS "storageLocationName"
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
                SELECT imei, status, source_reference
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
                SELECT serial_number, status, source_reference
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
                SELECT serial_number, status, source_reference
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


async def release_pending_inbound_identifiers(session: AsyncSession, source_reference: str) -> None:
    await session.execute(
        text(
            """
            DELETE FROM product_imeis
            WHERE source_reference = :source_reference
              AND status = 'PENDING_INBOUND'
            """
        ),
        {"source_reference": source_reference},
    )
    await session.execute(
        text(
            """
            DELETE FROM product_serial_numbers
            WHERE source_reference = :source_reference
              AND status = 'PENDING_INBOUND'
            """
        ),
        {"source_reference": source_reference},
    )


async def activate_pending_inbound_identifiers(session: AsyncSession, source_reference: str) -> None:
    await session.execute(
        text(
            """
            WITH pending AS (
                SELECT
                    pi.id,
                    ROW_NUMBER() OVER (
                        PARTITION BY pi.product_id, pi.variant_id
                        ORDER BY pi.created_at, pi.imei
                    ) AS row_no,
                    EXISTS (
                        SELECT 1
                        FROM product_imeis existing
                        WHERE existing.product_id = pi.product_id
                          AND (
                              existing.variant_id = pi.variant_id
                              OR (existing.variant_id IS NULL AND pi.variant_id IS NULL)
                          )
                          AND existing.is_primary = TRUE
                          AND existing.status <> 'PENDING_INBOUND'
                    ) AS has_primary
                FROM product_imeis pi
                WHERE pi.source_reference = :source_reference
                  AND pi.status = 'PENDING_INBOUND'
            )
            UPDATE product_imeis target
            SET status = 'IN_STOCK',
                is_primary = CASE
                    WHEN pending.row_no = 1 AND pending.has_primary = FALSE THEN TRUE
                    ELSE target.is_primary
                END,
                received_at = COALESCE(target.received_at, NOW()),
                updated_at = NOW()
            FROM pending
            WHERE target.id = pending.id
            """
        ),
        {"source_reference": source_reference},
    )
    await session.execute(
        text(
            """
            UPDATE product_serial_numbers
            SET status = 'IN_STOCK',
                received_at = COALESCE(received_at, NOW()),
                updated_at = NOW()
            WHERE source_reference = :source_reference
              AND status = 'PENDING_INBOUND'
            """
        ),
        {"source_reference": source_reference},
    )


async def assign_identifier_locations_for_receipt_line(
    session: AsyncSession,
    *,
    product_id: UUID,
    location_id: UUID,
    imeis: list[str],
    serial_numbers: list[str],
) -> None:
    if imeis:
        await session.execute(
            text(
                """
                UPDATE product_imeis
                SET location_id = :location_id,
                    updated_at = NOW()
                WHERE imei = ANY(:imeis)
                """
            ),
            {"location_id": location_id, "imeis": imeis},
        )
    if serial_numbers:
        await session.execute(
            text(
                """
                UPDATE product_serial_numbers
                SET location_id = :location_id,
                    updated_at = NOW()
                WHERE product_id = :product_id
                  AND serial_number = ANY(:serial_numbers)
                """
            ),
            {"product_id": product_id, "location_id": location_id, "serial_numbers": serial_numbers},
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
