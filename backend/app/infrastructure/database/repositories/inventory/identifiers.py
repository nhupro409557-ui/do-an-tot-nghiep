from .stock_mutation_common import *

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


async def insert_pending_product_imei(
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
                FALSE,
                'PENDING_INBOUND',
                :source_reference,
                NULL
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


async def insert_pending_product_serial_number(
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
                :id, :product_id, :variant_id, :serial_number, 'PENDING_INBOUND', :source_reference, NULL
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


async def upsert_product_identifier_pair(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    imei1: str,
    serial_number: str,
    source_reference: str | None,
    imei2: str | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_identifier_pairs (
                product_id, variant_id, imei1, imei2, serial_number, source_reference
            )
            VALUES (
                :product_id, :variant_id, :imei1, :imei2, :serial_number, :source_reference
            )
            ON CONFLICT (product_id, serial_number) DO UPDATE
            SET imei1 = EXCLUDED.imei1,
                imei2 = EXCLUDED.imei2,
                variant_id = EXCLUDED.variant_id,
                source_reference = COALESCE(EXCLUDED.source_reference, product_identifier_pairs.source_reference),
                updated_at = NOW()
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "imei1": imei1,
            "imei2": imei2,
            "serial_number": serial_number,
            "source_reference": source_reference,
        },
    )


async def get_identifier_pair_for_outbound(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    location_id: UUID,
    identifier_type: str,
    identifier_value: str,
) -> dict | None:
    normalized_type = identifier_type.upper()
    if normalized_type not in {"IMEI", "SERIAL"}:
        return None

    if normalized_type == "IMEI":
        predicate = "(pair.imei1 = :identifier_value OR pair.imei2 = :identifier_value)"
    else:
        predicate = "pair.serial_number = :identifier_value"

    result = await session.execute(
        text(
            f"""
            SELECT
                pair.imei1,
                pair.imei2,
                pair.imei1 AS imei,
                pair.serial_number AS "serialNumber",
                pi1.status AS "imei1Status",
                pi2.status AS "imei2Status",
                psn.status AS "serialStatus",
                pi1.location_id AS "imei1LocationId",
                pi2.location_id AS "imei2LocationId",
                psn.location_id AS "serialLocationId"
            FROM product_identifier_pairs pair
            JOIN product_imeis pi1
              ON pi1.product_id = pair.product_id
             AND pi1.variant_id IS NOT DISTINCT FROM pair.variant_id
             AND pi1.imei = pair.imei1
            LEFT JOIN product_imeis pi2
              ON pi2.product_id = pair.product_id
             AND pi2.variant_id IS NOT DISTINCT FROM pair.variant_id
             AND pi2.imei = pair.imei2
            JOIN product_serial_numbers psn
              ON psn.product_id = pair.product_id
             AND psn.variant_id IS NOT DISTINCT FROM pair.variant_id
             AND psn.serial_number = pair.serial_number
            WHERE pair.product_id = :product_id
              AND pair.variant_id IS NOT DISTINCT FROM :variant_id
              AND {predicate}
              AND pi1.status = 'IN_STOCK'
              AND (pair.imei2 IS NULL OR pi2.status = 'IN_STOCK')
              AND psn.status = 'IN_STOCK'
              AND pi1.location_id = :location_id
              AND (pair.imei2 IS NULL OR pi2.location_id = :location_id)
              AND psn.location_id = :location_id
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": location_id,
            "identifier_value": identifier_value,
        },
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def list_identifier_issue_candidates(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None = None,
    limit: int = 100,
) -> list[dict]:
    result = await session.execute(
        text(
            """
            WITH paired_candidates AS (
                SELECT
                    pair.serial_number AS value,
                    'SERIAL' AS "identifierType",
                    pair.imei1,
                    pair.imei2,
                    pair.serial_number AS "serialNumber",
                    pi1.location_id,
                    loc.code AS "locationCode",
                    loc.name AS "locationName",
                    COALESCE(
                        LEAST(pi1.received_at, psn.received_at, COALESCE(pi2.received_at, pi1.received_at)),
                        pi1.received_at,
                        psn.received_at,
                        pi2.received_at
                    ) AS "receivedAt",
                    0 AS priority
                FROM product_identifier_pairs pair
                JOIN product_imeis pi1
                  ON pi1.product_id = pair.product_id
                 AND pi1.variant_id IS NOT DISTINCT FROM pair.variant_id
                 AND pi1.imei = pair.imei1
                LEFT JOIN product_imeis pi2
                  ON pi2.product_id = pair.product_id
                 AND pi2.variant_id IS NOT DISTINCT FROM pair.variant_id
                 AND pi2.imei = pair.imei2
                JOIN product_serial_numbers psn
                  ON psn.product_id = pair.product_id
                 AND psn.variant_id IS NOT DISTINCT FROM pair.variant_id
                 AND psn.serial_number = pair.serial_number
                JOIN inventory_locations loc ON loc.id = pi1.location_id
                WHERE pair.product_id = :product_id
                  AND pair.variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
                  AND pi1.status = 'IN_STOCK'
                  AND (pair.imei2 IS NULL OR pi2.status = 'IN_STOCK')
                  AND psn.status = 'IN_STOCK'
                  AND pi1.location_id IS NOT NULL
                  AND psn.location_id = pi1.location_id
                  AND (pair.imei2 IS NULL OR pi2.location_id = pi1.location_id)
            ),
            standalone_imeis AS (
                SELECT
                    pi.imei AS value,
                    'IMEI' AS "identifierType",
                    pi.imei AS imei1,
                    NULL::varchar AS imei2,
                    NULL::varchar AS "serialNumber",
                    pi.location_id,
                    loc.code AS "locationCode",
                    loc.name AS "locationName",
                    pi.received_at AS "receivedAt",
                    1 AS priority
                FROM product_imeis pi
                JOIN inventory_locations loc ON loc.id = pi.location_id
                WHERE pi.product_id = :product_id
                  AND pi.variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
                  AND pi.status = 'IN_STOCK'
                  AND pi.location_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1
                      FROM product_identifier_pairs pair
                      WHERE pair.product_id = pi.product_id
                        AND pair.variant_id IS NOT DISTINCT FROM pi.variant_id
                        AND (pair.imei1 = pi.imei OR pair.imei2 = pi.imei)
                  )
            ),
            standalone_serials AS (
                SELECT
                    psn.serial_number AS value,
                    'SERIAL' AS "identifierType",
                    NULL::varchar AS imei1,
                    NULL::varchar AS imei2,
                    psn.serial_number AS "serialNumber",
                    psn.location_id,
                    loc.code AS "locationCode",
                    loc.name AS "locationName",
                    psn.received_at AS "receivedAt",
                    2 AS priority
                FROM product_serial_numbers psn
                JOIN inventory_locations loc ON loc.id = psn.location_id
                WHERE psn.product_id = :product_id
                  AND psn.variant_id IS NOT DISTINCT FROM CAST(:variant_id AS uuid)
                  AND psn.status = 'IN_STOCK'
                  AND psn.location_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1
                      FROM product_identifier_pairs pair
                      WHERE pair.product_id = psn.product_id
                        AND pair.variant_id IS NOT DISTINCT FROM psn.variant_id
                        AND pair.serial_number = psn.serial_number
                  )
            )
            SELECT
                value,
                "identifierType",
                imei1,
                imei2,
                "serialNumber",
                location_id AS "locationId",
                "locationCode",
                "locationName",
                "receivedAt"
            FROM (
                SELECT * FROM paired_candidates
                UNION ALL
                SELECT * FROM standalone_imeis
                UNION ALL
                SELECT * FROM standalone_serials
            ) candidates
            ORDER BY priority, "receivedAt" ASC NULLS LAST, value ASC
            LIMIT :limit
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "limit": max(1, int(limit or 1)),
        },
    )
    return [dict(row) for row in result.mappings().all()]


async def list_product_imeis_for_inventory(
    session: AsyncSession,
    product_id: UUID,
    variant_id: UUID | None = None,
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                pi.id,
                pi.imei AS value,
                pi.status,
                pi.is_primary AS "isPrimary",
                pi.source_reference AS "sourceReference",
                pi.received_at AS "receivedAt",
                pi.sold_at AS "soldAt",
                loc.id AS "locationId",
                loc.code AS "locationCode",
                loc.name AS "locationName",
                req.id AS "pendingRequestId",
                req.new_value AS "pendingNewValue",
                req.reason AS "pendingReason"
            FROM product_imeis pi
            LEFT JOIN inventory_locations loc ON loc.id = pi.location_id
            LEFT JOIN inventory_identifier_edit_requests req
              ON req.identifier_type = 'IMEI'
             AND req.identifier_id = pi.id
             AND req.status = 'PENDING'
            WHERE pi.product_id = :product_id
              AND (CAST(:variant_id AS uuid) IS NULL OR pi.variant_id = CAST(:variant_id AS uuid))
            ORDER BY pi.is_primary DESC, pi.received_at DESC NULLS LAST, pi.created_at DESC
            """
        ),
        {"product_id": product_id, "variant_id": variant_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_product_serial_numbers_for_inventory(
    session: AsyncSession,
    product_id: UUID,
    variant_id: UUID | None = None,
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                psn.id,
                psn.serial_number AS value,
                psn.status,
                psn.source_reference AS "sourceReference",
                psn.received_at AS "receivedAt",
                psn.sold_at AS "soldAt",
                loc.id AS "locationId",
                loc.code AS "locationCode",
                loc.name AS "locationName",
                req.id AS "pendingRequestId",
                req.new_value AS "pendingNewValue",
                req.reason AS "pendingReason"
            FROM product_serial_numbers psn
            LEFT JOIN inventory_locations loc ON loc.id = psn.location_id
            LEFT JOIN inventory_identifier_edit_requests req
              ON req.identifier_type = 'SERIAL'
             AND req.identifier_id = psn.id
             AND req.status = 'PENDING'
            WHERE psn.product_id = :product_id
              AND (CAST(:variant_id AS uuid) IS NULL OR psn.variant_id = CAST(:variant_id AS uuid))
            ORDER BY psn.received_at DESC NULLS LAST, psn.created_at DESC
            """
        ),
        {"product_id": product_id, "variant_id": variant_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_identifier_edit_requests(
    session: AsyncSession,
    *,
    status: str | None = None,
    product_id: UUID | None = None,
    variant_id: UUID | None = None,
    limit: int = 200,
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                req.id,
                req.identifier_type AS "identifierType",
                req.identifier_id AS "identifierId",
                req.product_id AS "productId",
                req.variant_id AS "variantId",
                req.current_value AS "currentValue",
                req.new_value AS "newValue",
                req.reason,
                req.status,
                req.decision_note AS "decisionNote",
                req.created_at AS "createdAt",
                req.decided_at AS "decidedAt",
                p.name AS "productName",
                p.sku AS "productSku",
                pv.sku AS "variantSku",
                pv.color_name AS "variantColor",
                pv.configuration AS "variantConfiguration"
            FROM inventory_identifier_edit_requests req
            JOIN products p ON p.id = req.product_id
            LEFT JOIN product_variants pv ON pv.id = req.variant_id
            WHERE (CAST(:status AS varchar) IS NULL OR req.status = CAST(:status AS varchar))
              AND (CAST(:product_id AS uuid) IS NULL OR req.product_id = CAST(:product_id AS uuid))
              AND (CAST(:variant_id AS uuid) IS NULL OR req.variant_id = CAST(:variant_id AS uuid))
            ORDER BY req.created_at DESC
            LIMIT :limit
            """
        ),
        {
            "status": status,
            "product_id": product_id,
            "variant_id": variant_id,
            "limit": max(1, min(int(limit or 200), 500)),
        },
    )
    return [dict(row) for row in result.mappings().all()]


async def get_identifier_for_edit(session: AsyncSession, identifier_type: str, identifier_id: UUID) -> dict | None:
    normalized_type = identifier_type.upper()
    if normalized_type == "IMEI":
        result = await session.execute(
            text(
                """
                SELECT
                    id,
                    product_id,
                    variant_id,
                    imei AS current_value
                FROM product_imeis
                WHERE id = :identifier_id
                """
            ),
            {"identifier_id": identifier_id},
        )
    elif normalized_type == "SERIAL":
        result = await session.execute(
            text(
                """
                SELECT
                    id,
                    product_id,
                    variant_id,
                    serial_number AS current_value
                FROM product_serial_numbers
                WHERE id = :identifier_id
                """
            ),
            {"identifier_id": identifier_id},
        )
    else:
        return None
    row = result.mappings().first()
    return dict(row) if row else None


async def has_pending_identifier_edit_request(session: AsyncSession, identifier_type: str, identifier_id: UUID) -> bool:
    result = await session.execute(
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
        {"identifier_type": identifier_type.upper(), "identifier_id": identifier_id},
    )
    return bool(result.scalar())


async def list_existing_imeis(session: AsyncSession, imeis: list[str]) -> list[str]:
    values = [str(value).strip() for value in imeis if str(value).strip()]
    if not values:
        return []
    result = await session.execute(
        text("SELECT imei FROM product_imeis WHERE imei = ANY(:values)"),
        {"values": values},
    )
    return [str(value) for value in result.scalars().all()]


async def list_existing_serial_numbers(
    session: AsyncSession,
    serial_numbers: list[str],
    *,
    product_id: UUID | None = None,
) -> list[str]:
    values = [str(value).strip() for value in serial_numbers if str(value).strip()]
    if not values:
        return []
    result = await session.execute(
        text(
            """
            SELECT serial_number
            FROM product_serial_numbers
            WHERE serial_number = ANY(:values)
              AND (CAST(:product_id AS uuid) IS NULL OR product_id = CAST(:product_id AS uuid))
            """
        ),
        {"values": values, "product_id": product_id},
    )
    return [str(value) for value in result.scalars().all()]


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
                id,
                identifier_type,
                identifier_id,
                product_id,
                variant_id,
                current_value,
                new_value,
                reason,
                status,
                requested_by,
                created_at
            )
            VALUES (
                :id,
                :identifier_type,
                :identifier_id,
                :product_id,
                :variant_id,
                :current_value,
                :new_value,
                :reason,
                'PENDING',
                :requested_by,
                NOW()
            )
            """
        ),
        {
            "id": request_id,
            "identifier_type": identifier_type.upper(),
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
    result = await session.execute(
        text(
            """
            SELECT
                id,
                identifier_type,
                identifier_id,
                product_id,
                variant_id,
                current_value,
                new_value,
                reason,
                status
            FROM inventory_identifier_edit_requests
            WHERE id = :request_id
            FOR UPDATE
            """
        ),
        {"request_id": request_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def update_identifier_value(session: AsyncSession, identifier_type: str, identifier_id: UUID, new_value: str) -> None:
    normalized_type = identifier_type.upper()
    if normalized_type == "IMEI":
        await session.execute(
            text("UPDATE product_imeis SET imei = :new_value, updated_at = NOW() WHERE id = :identifier_id"),
            {"identifier_id": identifier_id, "new_value": new_value},
        )
    elif normalized_type == "SERIAL":
        await session.execute(
            text(
                """
                UPDATE product_serial_numbers
                SET serial_number = :new_value,
                    updated_at = NOW()
                WHERE id = :identifier_id
                """
            ),
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
                decision_note = :decision_note,
                decided_at = NOW()
            WHERE id = :request_id
            """
        ),
        {
            "request_id": request_id,
            "status": status.upper(),
            "decided_by": decided_by,
            "decision_note": decision_note,
        },
    )
