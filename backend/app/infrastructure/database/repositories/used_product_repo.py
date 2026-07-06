import json
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def log_history(
    session: AsyncSession,
    *,
    intake_id: UUID | None,
    device_id: UUID | None,
    event_type: str,
    old_status: str | None,
    new_status: str | None,
    actor_id: UUID | None,
    note: str | None,
    metadata: dict | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO used_device_events (
                id, intake_request_id, device_id, event_type, old_status,
                new_status, actor_id, note, metadata, created_at
            )
            VALUES (
                :id, :intake_id, :device_id, :event_type, :old_status,
                :new_status, :actor_id, :note, CAST(:metadata AS JSONB), NOW()
            )
            """
        ),
        {
            "id": uuid4(),
            "intake_id": intake_id,
            "device_id": device_id,
            "event_type": event_type,
            "old_status": old_status,
            "new_status": new_status,
            "actor_id": actor_id,
            "note": note,
            "metadata": json.dumps(metadata or {}, ensure_ascii=False),
        },
    )


async def product_variant_exists(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
) -> bool:
    return bool(
        (
            await session.execute(
                text(
                    """
                    SELECT 1
                    FROM products p
                    WHERE p.id = :product_id
                      AND (
                        CAST(:variant_id AS uuid) IS NULL
                        OR EXISTS (
                            SELECT 1 FROM product_variants pv
                            WHERE pv.id = CAST(:variant_id AS uuid)
                              AND pv.product_id = p.id
                        )
                      )
                    """
                ),
                {"product_id": product_id, "variant_id": variant_id},
            )
        ).scalar_one_or_none()
    )


async def active_imei_exists(session: AsyncSession, imei: str) -> bool:
    return bool(
        (
            await session.execute(
                text(
                    """
                    SELECT 1
                    FROM used_device_intake_requests
                    WHERE imei = :imei
                      AND status NOT IN ('REJECTED', 'CANCELLED')
                    UNION ALL
                    SELECT 1 FROM used_devices WHERE imei = :imei
                    LIMIT 1
                    """
                ),
                {"imei": imei},
            )
        ).scalar_one_or_none()
    )


async def next_request_code(session: AsyncSession) -> str:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    TO_CHAR(CURRENT_DATE, 'YYYYMMDD') AS date_code,
                    COUNT(*) + 1 AS sequence
                FROM used_device_intake_requests
                WHERE created_at::date = CURRENT_DATE
                """
            )
        )
    ).mappings().one()
    return f"CU-{row['date_code']}-{int(row['sequence']):04d}"


async def insert_intake(
    session: AsyncSession,
    *,
    intake_id: UUID,
    request_code: str,
    payload,
    actor_id: UUID,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO used_device_intake_requests (
                id, request_code, source_type, seller_user_id, seller_name, seller_phone,
                original_order_id, return_request_id, product_id, variant_id, imei,
                serial_number, expected_price, note, created_by, updated_by
            )
            VALUES (
                :id, :request_code, :source_type, :seller_user_id, :seller_name, :seller_phone,
                :original_order_id, :return_request_id, :product_id, :variant_id, :imei,
                :serial_number, :expected_price, :note, :actor_id, :actor_id
            )
            """
        ),
        {
            "id": intake_id,
            "request_code": request_code,
            "source_type": payload.sourceType,
            "seller_user_id": payload.sellerUserId,
            "seller_name": payload.sellerName,
            "seller_phone": payload.sellerPhone,
            "original_order_id": payload.originalOrderId,
            "return_request_id": payload.returnRequestId,
            "product_id": payload.productId,
            "variant_id": payload.variantId,
            "imei": payload.imei,
            "serial_number": payload.serialNumber,
            "expected_price": payload.expectedPrice,
            "note": payload.note,
            "actor_id": actor_id,
        },
    )


async def insert_event(
    session: AsyncSession,
    *,
    intake_id: UUID | None = None,
    device_id: UUID | None = None,
    event_type: str,
    old_status: str | None,
    new_status: str | None,
    actor_id: UUID,
    note: str | None = None,
    metadata: dict | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO used_device_events (
                id, intake_request_id, device_id, event_type, old_status,
                new_status, actor_id, note, metadata
            )
            VALUES (
                :id, :intake_id, :device_id, :event_type, :old_status,
                :new_status, :actor_id, :note, CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "id": uuid4(),
            "intake_id": intake_id,
            "device_id": device_id,
            "event_type": event_type,
            "old_status": old_status,
            "new_status": new_status,
            "actor_id": actor_id,
            "note": note,
            "metadata": json.dumps(metadata or {}),
        },
    )


async def list_intakes(
    session: AsyncSession,
    *,
    status_value: str,
    search: str,
    page: int,
    limit: int,
) -> dict:
    offset = (page - 1) * limit
    search_value = f"%{search.strip()}%" if search.strip() else ""
    params = {
        "status": status_value.strip().upper(),
        "search": search_value,
        "limit": limit,
        "offset": offset,
    }
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    i.id, i.request_code AS "requestCode", i.source_type AS "sourceType",
                    i.seller_name AS "sellerName", i.seller_phone AS "sellerPhone",
                    i.product_id AS "productId", i.variant_id AS "variantId",
                    p.name AS "productName", p.sku AS "productSku",
                    pv.sku AS "variantSku", pv.color_name AS "colorName",
                    pv.storage, pv.ram, pv.configuration,
                    i.imei, i.serial_number AS "serialNumber",
                    i.expected_price::float AS "expectedPrice", i.note, i.status,
                    i.received_at AS "receivedAt", i.appraised_at AS "appraisedAt",
                    i.accepted_at AS "acceptedAt", i.created_at AS "createdAt",
                    latest.outcome AS "inspectionOutcome",
                    latest.condition_grade AS "conditionGrade",
                    latest.condition_score AS "conditionScore",
                    latest.battery_health AS "batteryHealth",
                    latest.repair_cost_estimate::float AS "repairCostEstimate",
                    latest.proposed_acquisition_price::float AS "proposedAcquisitionPrice",
                    latest.proposed_sale_price::float AS "proposedSalePrice",
                    latest.note AS "inspectionNote"
                FROM used_device_intake_requests i
                JOIN products p ON p.id = i.product_id
                LEFT JOIN product_variants pv ON pv.id = i.variant_id
                LEFT JOIN LATERAL (
                    SELECT *
                    FROM used_device_inspections inspection
                    WHERE inspection.intake_request_id = i.id
                    ORDER BY inspection.created_at DESC
                    LIMIT 1
                ) latest ON TRUE
                WHERE (:status = '' OR i.status = :status)
                  AND (
                    :search = ''
                    OR i.request_code ILIKE :search
                    OR i.imei ILIKE :search
                    OR COALESCE(i.serial_number, '') ILIKE :search
                    OR COALESCE(i.seller_name, '') ILIKE :search
                    OR p.name ILIKE :search
                  )
                ORDER BY i.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
    ).mappings().all()
    total = int(
        (
            await session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM used_device_intake_requests i
                    JOIN products p ON p.id = i.product_id
                    WHERE (:status = '' OR i.status = :status)
                      AND (
                        :search = ''
                        OR i.request_code ILIKE :search
                        OR i.imei ILIKE :search
                        OR COALESCE(i.serial_number, '') ILIKE :search
                        OR COALESCE(i.seller_name, '') ILIKE :search
                        OR p.name ILIKE :search
                      )
                    """
                ),
                params,
            )
        ).scalar_one()
    )
    return {"items": [dict(row) for row in rows], "page": page, "limit": limit, "total": total}


async def get_intake_for_update(session: AsyncSession, intake_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text("SELECT * FROM used_device_intake_requests WHERE id = :id FOR UPDATE"),
            {"id": intake_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_intake_status(
    session: AsyncSession,
    *,
    intake_id: UUID,
    status_value: str,
    actor_id: UUID,
) -> None:
    await session.execute(
        text(
            """
            UPDATE used_device_intake_requests
            SET status = CAST(:status AS varchar),
                updated_by = :actor_id,
                received_at = CASE WHEN CAST(:status AS varchar) = 'RECEIVED' THEN NOW() ELSE received_at END,
                appraised_at = CASE WHEN CAST(:status AS varchar) = 'APPRAISED' THEN NOW() ELSE appraised_at END,
                accepted_at = CASE WHEN CAST(:status AS varchar) = 'ACCEPTED' THEN NOW() ELSE accepted_at END,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": intake_id, "status": status_value, "actor_id": actor_id},
    )


async def insert_inspection(
    session: AsyncSession,
    *,
    inspection_id: UUID,
    intake_id: UUID,
    actor_id: UUID,
    payload,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO used_device_inspections (
                id, intake_request_id, inspector_id, outcome, condition_grade,
                condition_score, battery_health, checklist, evidence,
                repair_cost_estimate, proposed_acquisition_price,
                proposed_sale_price, note
            )
            VALUES (
                :id, :intake_id, :actor_id, :outcome, :condition_grade,
                :condition_score, :battery_health, CAST(:checklist AS jsonb),
                CAST(:evidence AS jsonb), :repair_cost_estimate,
                :proposed_acquisition_price, :proposed_sale_price, :note
            )
            """
        ),
        {
            "id": inspection_id,
            "intake_id": intake_id,
            "actor_id": actor_id,
            "outcome": payload.outcome,
            "condition_grade": payload.conditionGrade,
            "condition_score": payload.conditionScore,
            "battery_health": payload.batteryHealth,
            "checklist": json.dumps(payload.checklist),
            "evidence": json.dumps(payload.evidence),
            "repair_cost_estimate": payload.repairCostEstimate,
            "proposed_acquisition_price": payload.proposedAcquisitionPrice,
            "proposed_sale_price": payload.proposedSalePrice,
            "note": payload.note,
        },
    )


async def latest_appraisal(session: AsyncSession, intake_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT *
                FROM used_device_inspections
                WHERE intake_request_id = :intake_id
                  AND outcome = 'APPRAISED'
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"intake_id": intake_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def create_device_from_intake(
    session: AsyncSession,
    *,
    intake: dict,
    appraisal: dict,
    actor_id: UUID,
) -> UUID:
    device_id = uuid4()
    device_code = f"MC-{str(device_id).replace('-', '')[:10].upper()}"
    location_id = (
        await session.execute(
            text(
                """
                SELECT id
                FROM inventory_locations
                WHERE purpose = 'USED' AND status = 'ACTIVE'
                ORDER BY is_default DESC, sort_order, code
                LIMIT 1
                """
            )
        )
    ).scalar_one_or_none()
    if location_id is None:
        raise ValueError("Chưa cấu hình vị trí kho hàng cũ.")

    source = (
        await session.execute(
            text(
                """
                SELECT
                    p.name, p.sku, p.price::float AS product_price,
                    p.sale_price::float AS product_sale_price, p.specifications AS product_specs,
                    pv.sku AS variant_sku, pv.color_name, pv.storage, pv.ram,
                    pv.configuration, pv.specs AS variant_specs,
                    pv.price::float AS variant_price,
                    pv.sale_price::float AS variant_sale_price
                FROM products p
                LEFT JOIN product_variants pv ON pv.id = CAST(:variant_id AS uuid)
                WHERE p.id = :product_id
                """
            ),
            {"product_id": intake["product_id"], "variant_id": intake["variant_id"]},
        )
    ).mappings().one()
    original_list_price = Decimal(
        str(source["variant_price"] if source["variant_price"] is not None else source["product_price"] or 0)
    )
    current_sale = source["variant_sale_price"]
    if current_sale is None:
        current_sale = source["product_sale_price"]
    new_reference_price = Decimal(str(current_sale if current_sale is not None else original_list_price))
    acquisition_cost = Decimal(str(appraisal["proposed_acquisition_price"] or 0))
    refurbishment_cost = Decimal(str(appraisal["repair_cost_estimate"] or 0))
    sale_price = Decimal(str(appraisal["proposed_sale_price"] or 0))
    snapshot = {
        "productName": source["name"],
        "productSku": source["sku"],
        "variantSku": source["variant_sku"],
        "colorName": source["color_name"],
        "storage": source["storage"],
        "ram": source["ram"],
        "configuration": source["configuration"],
        "productSpecs": source["product_specs"] or {},
        "variantSpecs": source["variant_specs"] or {},
        "originalListPrice": float(original_list_price),
        "newReferencePrice": float(new_reference_price),
    }
    product_imei_id = (
        await session.execute(
            text("SELECT id FROM product_imeis WHERE imei = :imei LIMIT 1"),
            {"imei": intake["imei"]},
        )
    ).scalar_one_or_none()
    await session.execute(
        text(
            """
            INSERT INTO used_devices (
                id, device_code, intake_request_id, product_id, variant_id,
                product_imei_id, location_id, imei, serial_number,
                condition_grade, condition_score, battery_health,
                original_snapshot, acquisition_cost, refurbishment_cost,
                approved_sale_price
            )
            VALUES (
                :id, :device_code, :intake_id, :product_id, :variant_id,
                :product_imei_id, :location_id, :imei, :serial_number,
                :condition_grade, :condition_score, :battery_health,
                CAST(:snapshot AS jsonb), :acquisition_cost, :refurbishment_cost,
                :sale_price
            )
            """
        ),
        {
            "id": device_id,
            "device_code": device_code,
            "intake_id": intake["id"],
            "product_id": intake["product_id"],
            "variant_id": intake["variant_id"],
            "product_imei_id": product_imei_id,
            "location_id": location_id,
            "imei": intake["imei"],
            "serial_number": intake["serial_number"],
            "condition_grade": appraisal["condition_grade"],
            "condition_score": appraisal["condition_score"],
            "battery_health": appraisal["battery_health"],
            "snapshot": json.dumps(snapshot),
            "acquisition_cost": acquisition_cost,
            "refurbishment_cost": refurbishment_cost,
            "sale_price": sale_price,
        },
    )
    await session.execute(
        text(
            """
            INSERT INTO used_device_prices (
                id, device_id, original_list_price, new_reference_price,
                acquisition_cost, refurbishment_cost, proposed_sale_price,
                approved_sale_price, status, reason, created_by
            )
            VALUES (
                :id, :device_id, :original_list_price, :new_reference_price,
                :acquisition_cost, :refurbishment_cost, :sale_price,
                :sale_price, 'APPROVED', :reason, :actor_id
            )
            """
        ),
        {
            "id": uuid4(),
            "device_id": device_id,
            "original_list_price": original_list_price,
            "new_reference_price": new_reference_price,
            "acquisition_cost": acquisition_cost,
            "refurbishment_cost": refurbishment_cost,
            "sale_price": sale_price,
            "reason": appraisal["note"],
            "actor_id": actor_id,
        },
    )
    return device_id


async def list_devices(
    session: AsyncSession,
    *,
    status_value: str,
    search: str,
) -> list[dict]:
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    d.id, d.device_code AS "deviceCode", d.product_id AS "productId",
                    d.variant_id AS "variantId", p.name AS "productName",
                    p.sku AS "productSku", pv.sku AS "variantSku",
                    d.imei, d.serial_number AS "serialNumber",
                    d.condition_grade AS "conditionGrade",
                    d.condition_score AS "conditionScore",
                    d.battery_health AS "batteryHealth",
                    d.status, d.ownership_status AS "ownershipStatus",
                    d.original_snapshot AS "originalSnapshot",
                    d.acquisition_cost::float AS "acquisitionCost",
                    d.refurbishment_cost::float AS "refurbishmentCost",
                    d.approved_sale_price::float AS "approvedSalePrice",
                    loc.code AS "locationCode", loc.name AS "locationName",
                    inspection.checklist AS "inspectionChecklist",
                    inspection.evidence AS "inspectionEvidence",
                    listing.id AS "listingId", listing.slug AS "listingSlug",
                    listing.title AS "listingTitle",
                    listing.description AS "listingDescription",
                    listing.highlights AS "listingHighlights",
                    listing.images AS "listingImages",
                    listing.warranty_months AS "listingWarrantyMonths",
                    listing.price_comparison_note AS "priceComparisonNote",
                    listing.status AS "listingStatus",
                    d.created_at AS "createdAt"
                FROM used_devices d
                JOIN products p ON p.id = d.product_id
                LEFT JOIN product_variants pv ON pv.id = d.variant_id
                JOIN inventory_locations loc ON loc.id = d.location_id
                LEFT JOIN LATERAL (
                    SELECT checklist, evidence
                    FROM used_device_inspections i
                    WHERE i.intake_request_id = d.intake_request_id
                    ORDER BY i.created_at DESC
                    LIMIT 1
                ) inspection ON TRUE
                LEFT JOIN used_device_listings listing ON listing.device_id = d.id
                WHERE (:status = '' OR d.status = :status)
                  AND (
                    :search = ''
                    OR d.device_code ILIKE :search
                    OR d.imei ILIKE :search
                    OR COALESCE(d.serial_number, '') ILIKE :search
                    OR p.name ILIKE :search
                  )
                ORDER BY d.created_at DESC
                LIMIT 500
                """
            ),
            {
                "status": status_value.strip().upper(),
                "search": f"%{search.strip()}%" if search.strip() else "",
            },
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def list_device_history(session: AsyncSession, device_id: UUID) -> dict | None:
    device = (
        await session.execute(
            text(
                """
                SELECT
                    d.id, d.device_code AS "deviceCode", d.imei,
                    d.status, p.name AS "productName"
                FROM used_devices d
                JOIN products p ON p.id = d.product_id
                WHERE d.id = :device_id
                """
            ),
            {"device_id": device_id},
        )
    ).mappings().first()
    if not device:
        return None

    rows = (
        await session.execute(
            text(
                """
                SELECT *
                FROM (
                    SELECT
                        e.created_at AS "createdAt",
                        'EVENT' AS "entryType",
                        e.event_type AS "title",
                        e.old_status AS "oldStatus",
                        e.new_status AS "newStatus",
                        e.note,
                        e.metadata,
                        NULL::varchar AS "outcome",
                        NULL::varchar AS "conditionGrade",
                        NULL::int AS "conditionScore",
                        NULL::int AS "batteryHealth",
                        NULL::numeric AS "repairCostEstimate",
                        NULL::numeric AS "proposedSalePrice",
                        NULL::numeric AS "approvedSalePrice"
                    FROM used_device_events e
                    WHERE e.device_id = :device_id
                    UNION ALL
                    SELECT
                        i.created_at AS "createdAt",
                        'INSPECTION' AS "entryType",
                        'QC thiết bị' AS "title",
                        NULL::varchar AS "oldStatus",
                        NULL::varchar AS "newStatus",
                        i.note,
                        jsonb_build_object(
                            'checklist', i.checklist,
                            'evidence', i.evidence
                        ) AS metadata,
                        i.outcome,
                        i.condition_grade AS "conditionGrade",
                        i.condition_score AS "conditionScore",
                        i.battery_health AS "batteryHealth",
                        i.repair_cost_estimate AS "repairCostEstimate",
                        i.proposed_sale_price AS "proposedSalePrice",
                        NULL::numeric AS "approvedSalePrice"
                    FROM used_device_inspections i
                    JOIN used_devices d ON d.intake_request_id = i.intake_request_id
                    WHERE d.id = :device_id
                    UNION ALL
                    SELECT
                        p.created_at AS "createdAt",
                        'PRICE' AS "entryType",
                        'Cập nhật giá hàng cũ' AS "title",
                        NULL::varchar AS "oldStatus",
                        p.status AS "newStatus",
                        p.reason AS note,
                        jsonb_build_object(
                            'originalListPrice', p.original_list_price,
                            'newReferencePrice', p.new_reference_price,
                            'acquisitionCost', p.acquisition_cost,
                            'refurbishmentCost', p.refurbishment_cost,
                            'proposedSalePrice', p.proposed_sale_price,
                            'approvedSalePrice', p.approved_sale_price
                        ) AS metadata,
                        NULL::varchar AS "outcome",
                        NULL::varchar AS "conditionGrade",
                        NULL::int AS "conditionScore",
                        NULL::int AS "batteryHealth",
                        p.refurbishment_cost AS "repairCostEstimate",
                        p.proposed_sale_price AS "proposedSalePrice",
                        p.approved_sale_price AS "approvedSalePrice"
                    FROM used_device_prices p
                    WHERE p.device_id = :device_id
                ) history
                ORDER BY "createdAt" DESC
                LIMIT 200
                """
            ),
            {"device_id": device_id},
        )
    ).mappings().all()
    return {"device": dict(device), "items": [dict(row) for row in rows]}


async def get_device_for_listing(session: AsyncSession, device_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    d.*, p.name AS product_name, p.image_url AS product_image_url,
                    p.images AS product_images,
                    pv.color_name, pv.storage, pv.ram, pv.configuration,
                    inspection.evidence AS inspection_evidence
                FROM used_devices d
                JOIN products p ON p.id = d.product_id
                LEFT JOIN product_variants pv ON pv.id = d.variant_id
                LEFT JOIN LATERAL (
                    SELECT evidence
                    FROM used_device_inspections i
                    WHERE i.intake_request_id = d.intake_request_id
                    ORDER BY i.created_at DESC
                    LIMIT 1
                ) inspection ON TRUE
                WHERE d.id = :device_id
                FOR UPDATE OF d
                """
            ),
            {"device_id": device_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_device_status(session: AsyncSession, *, device_id: UUID, status_value: str) -> None:
    await session.execute(
        text(
            """
            UPDATE used_devices
            SET status = CAST(:status AS varchar),
                updated_at = NOW()
            WHERE id = :device_id
            """
        ),
        {"device_id": device_id, "status": status_value},
    )
    if status_value == "READY_FOR_PRICING":
        await session.execute(
            text(
                """
                UPDATE used_device_listings
                SET status = 'DRAFT',
                    updated_at = NOW(),
                    published_at = NULL
                WHERE device_id = :device_id
                  AND status <> 'DRAFT'
                """
            ),
            {"device_id": device_id},
        )


async def apply_device_reinspection(
    session: AsyncSession,
    *,
    inspection_id: UUID,
    device: dict,
    payload,
    actor_id: UUID,
) -> str:
    await insert_inspection(
        session,
        inspection_id=inspection_id,
        intake_id=device["intake_request_id"],
        actor_id=actor_id,
        payload=payload,
    )
    if payload.outcome == "APPRAISED":
        new_status = "READY_FOR_PRICING"
        await session.execute(
            text(
                """
                UPDATE used_devices
                SET status = :status,
                    condition_grade = :condition_grade,
                    condition_score = :condition_score,
                    battery_health = :battery_health,
                    refurbishment_cost = :refurbishment_cost,
                    approved_sale_price = :approved_sale_price,
                    updated_at = NOW()
                WHERE id = :device_id
                """
            ),
            {
                "device_id": device["id"],
                "status": new_status,
                "condition_grade": payload.conditionGrade,
                "condition_score": payload.conditionScore,
                "battery_health": payload.batteryHealth,
                "refurbishment_cost": payload.repairCostEstimate,
                "approved_sale_price": payload.proposedSalePrice,
            },
        )
        await session.execute(
            text(
                """
                UPDATE used_device_listings
                SET status = 'DRAFT',
                    updated_at = NOW(),
                    published_at = NULL
                WHERE device_id = :device_id
                  AND status <> 'DRAFT'
                """
            ),
            {"device_id": device["id"]},
        )
        snapshot = device["original_snapshot"] or {}
        original_list_price = Decimal(str(snapshot.get("originalListPrice") or 0))
        new_reference_price = Decimal(str(snapshot.get("newReferencePrice") or 0))
        await session.execute(
            text(
                """
                INSERT INTO used_device_prices (
                    id, device_id, original_list_price, new_reference_price,
                    acquisition_cost, refurbishment_cost, proposed_sale_price,
                    approved_sale_price, status, reason, created_by
                )
                VALUES (
                    :id, :device_id, :original_list_price, :new_reference_price,
                    :acquisition_cost, :refurbishment_cost, :proposed_sale_price,
                    :approved_sale_price, 'APPROVED', :reason, :actor_id
                )
                """
            ),
            {
                "id": uuid4(),
                "device_id": device["id"],
                "original_list_price": original_list_price,
                "new_reference_price": new_reference_price,
                "acquisition_cost": device["acquisition_cost"] or 0,
                "refurbishment_cost": payload.repairCostEstimate,
                "proposed_sale_price": payload.proposedSalePrice,
                "approved_sale_price": payload.proposedSalePrice,
                "reason": payload.note,
                "actor_id": actor_id,
            },
        )
        return new_status

    new_status = "REPAIRING" if payload.outcome == "REPAIR_REQUIRED" else "RETIRED"
    await session.execute(
        text(
            """
            UPDATE used_devices
            SET status = :status,
                condition_grade = COALESCE(:condition_grade, condition_grade),
                condition_score = COALESCE(:condition_score, condition_score),
                battery_health = COALESCE(:battery_health, battery_health),
                refurbishment_cost = :refurbishment_cost,
                updated_at = NOW()
            WHERE id = :device_id
            """
        ),
        {
            "device_id": device["id"],
            "status": new_status,
            "condition_grade": payload.conditionGrade,
            "condition_score": payload.conditionScore,
            "battery_health": payload.batteryHealth,
            "refurbishment_cost": payload.repairCostEstimate,
        },
    )
    return new_status


async def upsert_listing(
    session: AsyncSession,
    *,
    listing_id: UUID,
    device_id: UUID,
    slug: str,
    payload,
    actor_id: UUID,
) -> UUID:
    result = await session.execute(
        text(
            """
            INSERT INTO used_device_listings (
                id, device_id, slug, title, description, highlights, images,
                warranty_months, price_comparison_note, status, created_by, updated_by
            )
            VALUES (
                :id, :device_id, :slug, :title, :description,
                CAST(:highlights AS jsonb), CAST(:images AS jsonb),
                :warranty_months, :price_comparison_note, 'DRAFT', :actor_id, :actor_id
            )
            ON CONFLICT (device_id) DO UPDATE
            SET slug = EXCLUDED.slug,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                highlights = EXCLUDED.highlights,
                images = EXCLUDED.images,
                warranty_months = EXCLUDED.warranty_months,
                price_comparison_note = EXCLUDED.price_comparison_note,
                status = 'DRAFT',
                updated_by = EXCLUDED.updated_by,
                approved_by = NULL,
                published_at = NULL,
                updated_at = NOW()
            RETURNING id
            """
        ),
        {
            "id": listing_id,
            "device_id": device_id,
            "slug": slug,
            "title": payload.title.strip(),
            "description": payload.description.strip(),
            "highlights": json.dumps(payload.highlights, ensure_ascii=False),
            "images": json.dumps(payload.images, ensure_ascii=False),
            "warranty_months": payload.warrantyMonths,
            "price_comparison_note": payload.priceComparisonNote,
            "actor_id": actor_id,
        },
    )
    await session.execute(
        text(
            """
            UPDATE used_devices
            SET status = 'LISTING_DRAFT',
                warranty_months = :warranty_months,
                updated_at = NOW()
            WHERE id = :device_id
            """
        ),
        {"device_id": device_id, "warranty_months": payload.warrantyMonths},
    )
    return result.scalar_one()


async def get_listing_for_update(session: AsyncSession, listing_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text("SELECT * FROM used_device_listings WHERE id = :id FOR UPDATE"),
            {"id": listing_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_listing_status(
    session: AsyncSession,
    *,
    listing_id: UUID,
    device_id: UUID,
    status_value: str,
    device_status: str,
    actor_id: UUID,
) -> None:
    await session.execute(
        text(
            """
            UPDATE used_device_listings
            SET status = CAST(:status AS varchar),
                updated_by = :actor_id,
                approved_by = CASE
                    WHEN CAST(:status AS varchar) = 'PUBLISHED' THEN :actor_id
                    ELSE approved_by
                END,
                published_at = CASE
                    WHEN CAST(:status AS varchar) = 'PUBLISHED' THEN NOW()
                    ELSE published_at
                END,
                updated_at = NOW()
            WHERE id = :listing_id
            """
        ),
        {
            "listing_id": listing_id,
            "status": status_value,
            "actor_id": actor_id,
        },
    )
    await session.execute(
        text(
            """
            UPDATE used_devices
            SET status = CAST(:status AS varchar), updated_at = NOW()
            WHERE id = :device_id
            """
        ),
        {"device_id": device_id, "status": device_status},
    )


async def list_admin_listings(session: AsyncSession, *, status_value: str, search: str) -> list[dict]:
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    listing.id, listing.device_id AS "deviceId", listing.slug,
                    listing.title, listing.description, listing.highlights,
                    listing.images, listing.warranty_months AS "warrantyMonths",
                    listing.price_comparison_note AS "priceComparisonNote",
                    listing.status, listing.published_at AS "publishedAt",
                    d.device_code AS "deviceCode", d.imei,
                    d.condition_grade AS "conditionGrade",
                    d.condition_score AS "conditionScore",
                    d.battery_health AS "batteryHealth",
                    d.approved_sale_price::float AS "salePrice",
                    d.original_snapshot AS "originalSnapshot",
                    p.name AS "productName"
                FROM used_device_listings listing
                JOIN used_devices d ON d.id = listing.device_id
                JOIN products p ON p.id = d.product_id
                WHERE (:status = '' OR listing.status = :status)
                  AND (
                    :search = ''
                    OR listing.title ILIKE :search
                    OR listing.slug ILIKE :search
                    OR d.device_code ILIKE :search
                    OR d.imei ILIKE :search
                  )
                ORDER BY listing.updated_at DESC
                LIMIT 500
                """
            ),
            {
                "status": status_value.strip().upper(),
                "search": f"%{search.strip()}%" if search.strip() else "",
            },
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def list_published_devices(
    session: AsyncSession,
    *,
    search: str,
    grade: str,
    min_price: Decimal | None,
    max_price: Decimal | None,
    sort: str,
    page: int,
    limit: int,
) -> dict:
    order_by = {
        "price_asc": "d.approved_sale_price ASC, listing.published_at DESC",
        "price_desc": "d.approved_sale_price DESC, listing.published_at DESC",
        "newest": "listing.published_at DESC",
        "savings": "(COALESCE((d.original_snapshot->>'newReferencePrice')::numeric, 0) - d.approved_sale_price) DESC",
    }.get(sort, "listing.published_at DESC")
    params = {
        "search": f"%{search.strip()}%" if search.strip() else "",
        "grade": grade.strip().upper(),
        "min_price": min_price,
        "max_price": max_price,
        "limit": limit,
        "offset": (page - 1) * limit,
    }
    where_clause = """
        listing.status = 'PUBLISHED'
        AND d.status = 'READY_FOR_SALE'
        AND (:search = '' OR listing.title ILIKE :search OR p.name ILIKE :search)
        AND (:grade = '' OR d.condition_grade = :grade)
        AND (CAST(:min_price AS numeric) IS NULL OR d.approved_sale_price >= CAST(:min_price AS numeric))
        AND (CAST(:max_price AS numeric) IS NULL OR d.approved_sale_price <= CAST(:max_price AS numeric))
    """
    rows = (
        await session.execute(
            text(
                f"""
                SELECT
                    listing.id, listing.slug, listing.title, listing.description,
                    listing.highlights, listing.images,
                    listing.warranty_months AS "warrantyMonths",
                    d.device_code AS "deviceCode",
                    d.condition_grade AS "conditionGrade",
                    d.condition_score AS "conditionScore",
                    d.battery_health AS "batteryHealth",
                    d.approved_sale_price::float AS "salePrice",
                    d.original_snapshot AS "originalSnapshot",
                    p.name AS "productName"
                FROM used_device_listings listing
                JOIN used_devices d ON d.id = listing.device_id
                JOIN products p ON p.id = d.product_id
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
    ).mappings().all()
    total = int(
        (
            await session.execute(
                text(
                    f"""
                    SELECT COUNT(*)
                    FROM used_device_listings listing
                    JOIN used_devices d ON d.id = listing.device_id
                    JOIN products p ON p.id = d.product_id
                    WHERE {where_clause}
                    """
                ),
                params,
            )
        ).scalar_one()
    )
    return {
        "items": [dict(row) for row in rows],
        "page": page,
        "limit": limit,
        "total": total,
    }


async def get_published_device(session: AsyncSession, slug: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    listing.id, listing.device_id AS "deviceId",
                    listing.slug, listing.title, listing.description,
                    listing.highlights, listing.images,
                    listing.warranty_months AS "warrantyMonths",
                    listing.price_comparison_note AS "priceComparisonNote",
                    listing.published_at AS "publishedAt",
                    d.device_code AS "deviceCode", d.imei,
                    d.condition_grade AS "conditionGrade",
                    d.condition_score AS "conditionScore",
                    d.battery_health AS "batteryHealth",
                    d.approved_sale_price::float AS "salePrice",
                    d.refurbishment_cost::float AS "refurbishmentCost",
                    d.original_snapshot AS "originalSnapshot",
                    inspection.checklist AS "inspectionChecklist",
                    p.id AS "productId", p.name AS "productName",
                    p.description AS "productDescription"
                FROM used_device_listings listing
                JOIN used_devices d ON d.id = listing.device_id
                JOIN products p ON p.id = d.product_id
                LEFT JOIN LATERAL (
                    SELECT checklist
                    FROM used_device_inspections i
                    WHERE i.intake_request_id = d.intake_request_id
                    ORDER BY i.created_at DESC
                    LIMIT 1
                ) inspection ON TRUE
                WHERE listing.slug = :slug
                  AND listing.status = 'PUBLISHED'
                  AND d.status = 'READY_FOR_SALE'
                """
            ),
            {"slug": slug},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_checkout_device(session: AsyncSession, device_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    d.id,
                    d.device_code AS "deviceCode",
                    d.product_id AS "productId",
                    d.variant_id AS "variantId",
                    d.approved_sale_price::float AS "salePrice",
                    GREATEST(COALESCE(listing.warranty_months, 0), 0) AS "warrantyMonths",
                    listing.title
                FROM used_devices d
                JOIN used_device_listings listing ON listing.device_id = d.id
                WHERE d.id = :device_id
                  AND d.status = 'READY_FOR_SALE'
                  AND listing.status = 'PUBLISHED'
                """
            ),
            {"device_id": device_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def reserve_device_for_order(
    session: AsyncSession,
    *,
    device_id: UUID,
    order_id: UUID,
    order_code: str,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                UPDATE used_devices d
                SET status = 'RESERVED',
                    updated_at = NOW()
                FROM used_device_listings listing
                WHERE d.id = listing.device_id
                  AND d.id = :device_id
                  AND d.status = 'READY_FOR_SALE'
                  AND listing.status = 'PUBLISHED'
                RETURNING
                    d.id,
                    d.device_code AS "deviceCode",
                    d.product_id AS "productId",
                    d.variant_id AS "variantId",
                    d.approved_sale_price::float AS "salePrice",
                    GREATEST(COALESCE(listing.warranty_months, 0), 0) AS "warrantyMonths",
                    listing.title
                """
            ),
            {"device_id": device_id},
        )
    ).mappings().first()
    if row:
        await log_history(
            session,
            intake_id=None,
            device_id=device_id,
            event_type="DEVICE_RESERVED",
            old_status="READY_FOR_SALE",
            new_status="RESERVED",
            actor_id=None,
            note=f"Giữ thiết bị cho đơn hàng {order_code}.",
            metadata={"orderId": str(order_id), "orderCode": order_code},
        )
    return dict(row) if row else None


async def mark_order_devices_sold(session: AsyncSession, *, order_id: UUID, order_code: str) -> None:
    rows = (
        await session.execute(
            text(
                """
                UPDATE used_devices d
                SET status = 'SOLD',
                    updated_at = NOW()
                FROM order_items oi
                WHERE oi.used_device_id = d.id
                  AND oi.order_id = :order_id
                  AND d.status = 'RESERVED'
                RETURNING d.id
                """
            ),
            {"order_id": order_id},
        )
    ).mappings().all()
    for row in rows:
        await log_history(
            session,
            intake_id=None,
            device_id=row["id"],
            event_type="DEVICE_SOLD",
            old_status="RESERVED",
            new_status="SOLD",
            actor_id=None,
            note=f"Thiết bị đã bán theo đơn hàng {order_code}.",
            metadata={"orderId": str(order_id), "orderCode": order_code},
        )


async def mark_order_devices_returned_qc(session: AsyncSession, *, order_id: UUID, order_code: str) -> None:
    rows = (
        await session.execute(
            text(
                """
                UPDATE used_devices d
                SET status = 'RETURNED_QC',
                    updated_at = NOW()
                FROM order_items oi
                WHERE oi.used_device_id = d.id
                  AND oi.order_id = :order_id
                  AND d.status = 'SOLD'
                RETURNING d.id
                """
            ),
            {"order_id": order_id},
        )
    ).mappings().all()
    for row in rows:
        await log_history(
            session,
            intake_id=None,
            device_id=row["id"],
            event_type="DEVICE_RETURNED_QC",
            old_status="SOLD",
            new_status="RETURNED_QC",
            actor_id=None,
            note=f"Thiết bị hàng cũ được hoàn về QC từ đơn {order_code}.",
            metadata={"orderId": str(order_id), "orderCode": order_code},
        )


async def release_order_device_reservations(session: AsyncSession, *, order_id: UUID, order_code: str) -> None:
    rows = (
        await session.execute(
            text(
                """
                UPDATE used_devices d
                SET status = 'READY_FOR_SALE',
                    updated_at = NOW()
                FROM order_items oi
                WHERE oi.used_device_id = d.id
                  AND oi.order_id = :order_id
                  AND d.status = 'RESERVED'
                RETURNING d.id
                """
            ),
            {"order_id": order_id},
        )
    ).mappings().all()
    for row in rows:
        await log_history(
            session,
            intake_id=None,
            device_id=row["id"],
            event_type="DEVICE_RESERVATION_RELEASED",
            old_status="RESERVED",
            new_status="READY_FOR_SALE",
            actor_id=None,
            note=f"Giải phóng giữ hàng do đơn {order_code} không tiếp tục.",
            metadata={"orderId": str(order_id), "orderCode": order_code},
        )


async def list_source_products(session: AsyncSession, search: str) -> list[dict]:
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    p.id, p.name, p.sku, p.price::float AS price,
                    p.sale_price::float AS "salePrice",
                    COALESCE(
                        jsonb_agg(
                            jsonb_build_object(
                                'id', pv.id,
                                'sku', pv.sku,
                                'colorName', pv.color_name,
                                'storage', pv.storage,
                                'ram', pv.ram,
                                'configuration', pv.configuration,
                                'price', pv.price::float,
                                'salePrice', pv.sale_price::float
                            )
                            ORDER BY pv.created_at
                        ) FILTER (WHERE pv.id IS NOT NULL),
                        '[]'::jsonb
                    ) AS variants
                FROM products p
                LEFT JOIN product_variants pv
                    ON pv.product_id = p.id
                   AND pv.deleted_at IS NULL
                WHERE p.deleted_at IS NULL
                  AND (:search = '' OR p.name ILIKE :search OR p.sku ILIKE :search)
                GROUP BY p.id
                ORDER BY p.name
                LIMIT 200
                """
            ),
            {"search": f"%{search.strip()}%" if search.strip() else ""},
        )
    ).mappings().all()
    return [dict(row) for row in rows]
