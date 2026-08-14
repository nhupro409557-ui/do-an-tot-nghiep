from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id, get_user_permissions, require_permission
from app.application.after_sales import service
from app.application.after_sales.identifier_groups import (
    lock_identifier_group,
    update_locked_identifier_group_status,
)
from app.application.after_sales.schemas import (
    AfterSalesTimelineNoteRequest,
    ImeiDispositionRequest,
    InspectAfterSalesRequest,
    RepairedDeviceUsedIntakeRequest,
    UpdateAfterSalesStatusRequest,
)
from app.infrastructure.database.session import get_session


router = APIRouter(
    prefix="/after-sales",
    tags=["Admin - Hậu mãi"],
    dependencies=[Depends(require_permission("after_sales:read"))],
)


@router.get("/returns")
async def list_returns(
    status_value: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.list_requests(
        session, kind="RETURN", user_id=None, status_value=status_value,
        page=page, limit=limit, sort="-created_at",
    )


@router.patch("/returns/{request_id}/status", dependencies=[Depends(require_permission("after_sales:update"))])
async def update_return(
    request_id: UUID,
    payload: UpdateAfterSalesStatusRequest,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    permissions: set[str] = Depends(get_user_permissions),
) -> dict:
    target = payload.status.strip().upper()
    if target == "REFUND_PROCESSING" and "after_sales:refund" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xử lý hoàn tiền hậu mãi.")
    if target in {"EXCHANGE_PROCESSING", "QC_APPROVED"} and "after_sales:exchange" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xử lý đổi sản phẩm.")
    return await service.admin_update_status(
        session, kind="RETURN", request_id=request_id, actor_id=actor_id, payload=payload,
    )


@router.post("/returns/{request_id}/inspection", dependencies=[Depends(require_permission("after_sales:inspect"))])
async def inspect_return(
    request_id: UUID,
    payload: InspectAfterSalesRequest,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    permissions: set[str] = Depends(get_user_permissions),
) -> dict:
    result = payload.result.strip().upper()
    if result == "APPROVE_REFUND" and "after_sales:refund" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xử lý hoàn tiền hậu mãi.")
    if result == "APPROVE_EXCHANGE" and "after_sales:exchange" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xử lý đổi sản phẩm.")
    return await service.inspect_request(
        session, kind="RETURN", request_id=request_id, actor_id=actor_id, payload=payload,
    )


@router.get("/returns/{request_id}/events")
async def list_return_events(
    request_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await service.list_request_events(session, kind="RETURN", request_id=request_id)


@router.post("/returns/{request_id}/events", status_code=201, dependencies=[Depends(require_permission("after_sales:update"))])
async def add_return_event(
    request_id: UUID,
    payload: AfterSalesTimelineNoteRequest,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.add_request_timeline_note(
        session, kind="RETURN", request_id=request_id, actor_id=actor_id, payload=payload,
    )


@router.get("/warranties")
async def list_warranties(
    status_value: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.list_requests(
        session, kind="WARRANTY", user_id=None, status_value=status_value,
        page=page, limit=limit, sort="-created_at",
    )


@router.patch("/warranties/{request_id}/status", dependencies=[Depends(require_permission("after_sales:update"))])
async def update_warranty(
    request_id: UUID,
    payload: UpdateAfterSalesStatusRequest,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    permissions: set[str] = Depends(get_user_permissions),
) -> dict:
    target = payload.status.strip().upper()
    if target == "QC_IN_PROGRESS" and "after_sales:inspect" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền đánh giá lại QC bảo hành.")
    if target in {"REPLACEMENT_APPROVED", "REPLACEMENT_PROCESSING"} and "after_sales:exchange" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xử lý đổi sản phẩm.")
    return await service.admin_update_status(
        session, kind="WARRANTY", request_id=request_id, actor_id=actor_id, payload=payload,
    )


@router.post("/warranties/{request_id}/inspection", dependencies=[Depends(require_permission("after_sales:inspect"))])
async def inspect_warranty(
    request_id: UUID,
    payload: InspectAfterSalesRequest,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    permissions: set[str] = Depends(get_user_permissions),
) -> dict:
    result = payload.result.strip().upper()
    if result == "APPROVE_REPLACEMENT" and "after_sales:exchange" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xử lý đổi sản phẩm.")
    return await service.inspect_request(
        session, kind="WARRANTY", request_id=request_id, actor_id=actor_id, payload=payload,
    )


@router.get(
    "/warranties/{request_id}/replacement-candidates",
    dependencies=[Depends(require_permission("after_sales:exchange"))],
)
async def list_warranty_replacement_candidates(
    request_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.list_warranty_replacement_candidates(
        session,
        request_id=request_id,
    )


@router.get("/warranties/{request_id}/events")
async def list_warranty_events(
    request_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await service.list_request_events(session, kind="WARRANTY", request_id=request_id)


@router.post("/warranties/{request_id}/events", status_code=201, dependencies=[Depends(require_permission("after_sales:update"))])
async def add_warranty_event(
    request_id: UUID,
    payload: AfterSalesTimelineNoteRequest,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.add_request_timeline_note(
        session, kind="WARRANTY", request_id=request_id, actor_id=actor_id, payload=payload,
    )


@router.get("/defective-identifiers")
async def defective_identifiers(
    status_value: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT pi.id::text id, 'IMEI' type, pi.imei identifier, pi.status,
                   COALESCE('PAIR:' || pair.id::text, 'IMEI:' || pi.id::text) AS "deviceKey",
                   p.name AS "productName", pi.received_at AS "receivedAt",
                   cost.average_unit_cost AS "averageUnitCost",
                   COALESCE(latest.event, '{}'::jsonb) AS "latestDisposition",
                   pi.updated_at
            FROM product_imeis pi
            JOIN products p ON p.id=pi.product_id
            LEFT JOIN product_identifier_pairs pair
              ON pair.product_id = pi.product_id
             AND pair.variant_id IS NOT DISTINCT FROM pi.variant_id
             AND (pair.imei1 = pi.imei OR pair.imei2 = pi.imei)
            LEFT JOIN LATERAL (
                SELECT il.average_unit_cost
                FROM inventory_levels il
                WHERE il.variant_id IS NOT DISTINCT FROM pi.variant_id
                  AND (
                      il.product_id IS NOT DISTINCT FROM pi.product_id
                      OR (pi.variant_id IS NOT NULL AND il.product_id IS NULL)
                  )
                  AND (pi.location_id IS NULL OR il.location_id IS NOT DISTINCT FROM pi.location_id)
                ORDER BY
                    (pi.location_id IS NOT NULL AND il.location_id IS NOT DISTINCT FROM pi.location_id) DESC,
                    (COALESCE(il.average_unit_cost, 0) > 0) DESC,
                    il.updated_at DESC
                LIMIT 1
            ) cost ON TRUE
            LEFT JOIN LATERAL (
                SELECT jsonb_build_object(
                    'oldStatus', ev.old_status,
                    'newStatus', ev.new_status,
                    'reason', ev.reason,
                    'documentReference', ev.document_reference,
                    'partnerName', ev.partner_name,
                    'recoveryValue', COALESCE(ev.recovery_value, 0),
                    'actorId', ev.actor_id::text,
                    'createdAt', ev.created_at
                ) AS event
                FROM imei_disposition_events ev
                WHERE ev.imei_id = pi.id
                ORDER BY ev.created_at DESC
                LIMIT 1
            ) latest ON TRUE
            WHERE pi.status IN (
                'DEFECTIVE_RETURNED','INSPECTION_PENDING','REPAIR_PENDING','RTV_PENDING',
                'LIQUIDATION_PENDING','REPAIRED','RTV_COMPLETED','LIQUIDATED','SCRAP','OUT_OF_SYSTEM'
            ) AND (CAST(:status AS VARCHAR) IS NULL OR pi.status=CAST(:status AS VARCHAR))

            UNION ALL

            SELECT ps.id::text id, 'SERIAL' type, ps.serial_number identifier, ps.status,
                   COALESCE('PAIR:' || pair.id::text, 'SERIAL:' || ps.id::text) AS "deviceKey",
                   p.name AS "productName", ps.received_at AS "receivedAt",
                   cost.average_unit_cost AS "averageUnitCost",
                   COALESCE(latest.event, '{}'::jsonb) AS "latestDisposition",
                   ps.updated_at
            FROM product_serial_numbers ps
            JOIN products p ON p.id=ps.product_id
            LEFT JOIN product_identifier_pairs pair
              ON pair.product_id = ps.product_id
             AND pair.variant_id IS NOT DISTINCT FROM ps.variant_id
             AND pair.serial_number = ps.serial_number
            LEFT JOIN LATERAL (
                SELECT il.average_unit_cost
                FROM inventory_levels il
                WHERE il.variant_id IS NOT DISTINCT FROM ps.variant_id
                  AND (
                      il.product_id IS NOT DISTINCT FROM ps.product_id
                      OR (ps.variant_id IS NOT NULL AND il.product_id IS NULL)
                  )
                  AND (ps.location_id IS NULL OR il.location_id IS NOT DISTINCT FROM ps.location_id)
                ORDER BY
                    (ps.location_id IS NOT NULL AND il.location_id IS NOT DISTINCT FROM ps.location_id) DESC,
                    (COALESCE(il.average_unit_cost, 0) > 0) DESC,
                    il.updated_at DESC
                LIMIT 1
            ) cost ON TRUE
            LEFT JOIN LATERAL (
                SELECT jsonb_build_object(
                    'oldStatus', ev.old_status,
                    'newStatus', ev.new_status,
                    'reason', ev.reason,
                    'documentReference', ev.document_reference,
                    'partnerName', ev.partner_name,
                    'recoveryValue', COALESCE(ev.recovery_value, 0),
                    'actorId', ev.actor_id::text,
                    'createdAt', ev.created_at
                ) AS event
                FROM imei_disposition_events ev
                WHERE ev.serial_id = ps.id
                ORDER BY ev.created_at DESC
                LIMIT 1
            ) latest ON TRUE
            WHERE ps.status IN (
                'DEFECTIVE_RETURNED','INSPECTION_PENDING','REPAIR_PENDING','RTV_PENDING',
                'LIQUIDATION_PENDING','REPAIRED','RTV_COMPLETED','LIQUIDATED','SCRAP','OUT_OF_SYSTEM'
            ) AND (CAST(:status AS VARCHAR) IS NULL OR ps.status=CAST(:status AS VARCHAR))
            ORDER BY updated_at DESC
            """
        ),
        {"status": status_value},
    )
    rows = [dict(row._mapping) for row in result]
    if not rows:
        return rows
    intake_rows = (
        await session.execute(
            text(
                """
                SELECT id::text AS id, request_code AS "requestCode", status,
                       imei, serial_number
                FROM used_device_intake_requests
                WHERE status NOT IN ('REJECTED', 'CANCELLED')
                  AND (
                    imei = ANY(CAST(:values AS VARCHAR[]))
                    OR serial_number = ANY(CAST(:values AS VARCHAR[]))
                  )
                """
            ),
            {"values": [str(row["identifier"]) for row in rows]},
        )
    ).mappings().all()
    intake_by_identifier = {}
    for intake in intake_rows:
        intake_data = {key: value for key, value in intake.items() if key not in {"imei", "serial_number"}}
        if intake["imei"]:
            intake_by_identifier[intake["imei"]] = intake_data
        if intake["serial_number"]:
            intake_by_identifier[intake["serial_number"]] = intake_data
    for row in rows:
        row["usedIntake"] = intake_by_identifier.get(row["identifier"])
    return rows


@router.post(
    "/defective-identifiers/{identifier_id}/used-intake",
    dependencies=[
        Depends(require_permission("after_sales:update")),
        Depends(require_permission("used_product:manage")),
    ],
)
async def create_repaired_used_intake(
    identifier_id: UUID,
    payload: RepairedDeviceUsedIntakeRequest,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if not payload.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Cần xác nhận chuyển máy đã sửa sang quy trình hàng cũ.",
        )
    from app.application.after_sales.used_intake import create_repaired_device_used_intake

    return await create_repaired_device_used_intake(
        session,
        identifier_id=identifier_id,
        actor_id=actor_id,
        note=payload.note,
    )


@router.get("/reports/defective-disposition")
async def defective_disposition_report(
    session: AsyncSession = Depends(get_session),
) -> dict:
    base_sql = """
        WITH latest AS (
            SELECT DISTINCT ON (identifier_id)
                COALESCE(imei_id, serial_id) AS identifier_id,
                document_reference,
                partner_name,
                COALESCE(recovery_value, 0) AS recovery_value,
                created_at
            FROM imei_disposition_events
            ORDER BY COALESCE(imei_id, serial_id), created_at DESC, id DESC
        ),
        identifier_base AS (
            SELECT
                pi.id,
                COALESCE('PAIR:' || pair.id::text, 'IMEI:' || pi.id::text) AS device_key,
                pi.status,
                pi.product_id,
                p.name AS product_name,
                COALESCE(b.name, NULLIF(p.brand, ''), 'Chưa có brand') AS brand_name,
                COALESCE(cost.average_unit_cost, 0) AS average_unit_cost,
                COALESCE(latest.recovery_value, 0) AS recovery_value,
                latest.document_reference,
                latest.partner_name
            FROM product_imeis pi
            JOIN products p ON p.id = pi.product_id
            LEFT JOIN brands b ON b.id = p.brand_id
            LEFT JOIN product_identifier_pairs pair
              ON pair.product_id = pi.product_id
             AND pair.variant_id IS NOT DISTINCT FROM pi.variant_id
             AND (pair.imei1 = pi.imei OR pair.imei2 = pi.imei)
            LEFT JOIN latest ON latest.identifier_id = pi.id
            LEFT JOIN LATERAL (
                SELECT il.average_unit_cost
                FROM inventory_levels il
                WHERE il.variant_id IS NOT DISTINCT FROM pi.variant_id
                  AND (
                      il.product_id IS NOT DISTINCT FROM pi.product_id
                      OR (pi.variant_id IS NOT NULL AND il.product_id IS NULL)
                  )
                  AND (pi.location_id IS NULL OR il.location_id IS NOT DISTINCT FROM pi.location_id)
                ORDER BY
                    (pi.location_id IS NOT NULL AND il.location_id IS NOT DISTINCT FROM pi.location_id) DESC,
                    (COALESCE(il.average_unit_cost, 0) > 0) DESC,
                    il.updated_at DESC
                LIMIT 1
            ) cost ON TRUE
            WHERE pi.status IN (
                'DEFECTIVE_RETURNED','INSPECTION_PENDING','REPAIR_PENDING','RTV_PENDING',
                'LIQUIDATION_PENDING','REPAIRED','RTV_COMPLETED','LIQUIDATED','SCRAP','OUT_OF_SYSTEM'
            )

            UNION ALL

            SELECT
                ps.id,
                COALESCE('PAIR:' || pair.id::text, 'SERIAL:' || ps.id::text) AS device_key,
                ps.status,
                ps.product_id,
                p.name AS product_name,
                COALESCE(b.name, NULLIF(p.brand, ''), 'Chưa có brand') AS brand_name,
                COALESCE(cost.average_unit_cost, 0) AS average_unit_cost,
                COALESCE(latest.recovery_value, 0) AS recovery_value,
                latest.document_reference,
                latest.partner_name
            FROM product_serial_numbers ps
            JOIN products p ON p.id = ps.product_id
            LEFT JOIN brands b ON b.id = p.brand_id
            LEFT JOIN product_identifier_pairs pair
              ON pair.product_id = ps.product_id
             AND pair.variant_id IS NOT DISTINCT FROM ps.variant_id
             AND pair.serial_number = ps.serial_number
            LEFT JOIN latest ON latest.identifier_id = ps.id
            LEFT JOIN LATERAL (
                SELECT il.average_unit_cost
                FROM inventory_levels il
                WHERE il.variant_id IS NOT DISTINCT FROM ps.variant_id
                  AND (
                      il.product_id IS NOT DISTINCT FROM ps.product_id
                      OR (ps.variant_id IS NOT NULL AND il.product_id IS NULL)
                  )
                  AND (ps.location_id IS NULL OR il.location_id IS NOT DISTINCT FROM ps.location_id)
                ORDER BY
                    (ps.location_id IS NOT NULL AND il.location_id IS NOT DISTINCT FROM ps.location_id) DESC,
                    (COALESCE(il.average_unit_cost, 0) > 0) DESC,
                    il.updated_at DESC
                LIMIT 1
            ) cost ON TRUE
            WHERE ps.status IN (
                'DEFECTIVE_RETURNED','INSPECTION_PENDING','REPAIR_PENDING','RTV_PENDING',
                'LIQUIDATION_PENDING','REPAIRED','RTV_COMPLETED','LIQUIDATED','SCRAP','OUT_OF_SYSTEM'
            )
        ),
        base AS (
            SELECT DISTINCT ON (device_key)
                id, device_key, status, product_id, product_name, brand_name,
                average_unit_cost, recovery_value, document_reference, partner_name
            FROM identifier_base
            ORDER BY device_key,
                     (document_reference IS NOT NULL AND document_reference <> '') DESC,
                     recovery_value DESC,
                     id
        )
    """
    summary = (await session.execute(
        text(
            base_sql
            + """
            SELECT
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE status IN ('REPAIRED','RTV_COMPLETED','LIQUIDATED','SCRAP','OUT_OF_SYSTEM'))::int AS completed,
                COUNT(*) FILTER (WHERE status NOT IN ('REPAIRED','RTV_COMPLETED','LIQUIDATED','SCRAP','OUT_OF_SYSTEM'))::int AS processing,
                COUNT(*) FILTER (WHERE document_reference IS NOT NULL AND document_reference <> '')::int AS documented,
                COUNT(*) FILTER (WHERE recovery_value > 0)::int AS recovered,
                COALESCE(SUM(average_unit_cost), 0) AS "inventoryValue",
                COALESCE(SUM(recovery_value), 0) AS "recoveryValue",
                COALESCE(SUM(average_unit_cost) - SUM(recovery_value), 0) AS "netLossValue"
            FROM base
            """
        )
    )).mappings().first()
    by_status = (await session.execute(
        text(
            base_sql
            + """
            SELECT
                status,
                COUNT(*)::int AS count,
                COALESCE(SUM(average_unit_cost), 0) AS "inventoryValue",
                COALESCE(SUM(recovery_value), 0) AS "recoveryValue"
            FROM base
            GROUP BY status
            ORDER BY count DESC, status ASC
            """
        )
    )).mappings().all()
    by_brand = (await session.execute(
        text(
            base_sql
            + """
            SELECT
                brand_name AS "brandName",
                COUNT(*)::int AS count,
                COALESCE(SUM(average_unit_cost), 0) AS "inventoryValue",
                COALESCE(SUM(recovery_value), 0) AS "recoveryValue"
            FROM base
            GROUP BY brand_name
            ORDER BY count DESC, "inventoryValue" DESC, brand_name ASC
            LIMIT 8
            """
        )
    )).mappings().all()
    top_products = (await session.execute(
        text(
            base_sql
            + """
            SELECT
                product_id::text AS "productId",
                product_name AS "productName",
                brand_name AS "brandName",
                COUNT(*)::int AS count,
                COALESCE(SUM(average_unit_cost), 0) AS "inventoryValue",
                COALESCE(SUM(recovery_value), 0) AS "recoveryValue",
                COALESCE(SUM(average_unit_cost) - SUM(recovery_value), 0) AS "netLossValue"
            FROM base
            GROUP BY product_id, product_name, brand_name
            ORDER BY count DESC, "netLossValue" DESC, product_name ASC
            LIMIT 8
            """
        )
    )).mappings().all()
    return {
        "summary": dict(summary) if summary else {},
        "byStatus": [dict(row) for row in by_status],
        "byBrand": [dict(row) for row in by_brand],
        "topProducts": [dict(row) for row in top_products],
    }


@router.get("/defective-identifiers/{identifier_id}/disposition-events")
async def list_disposition_events(
    identifier_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT *
            FROM (
                SELECT DISTINCT ON (
                    ev.old_status, ev.new_status, ev.reason, ev.document_reference,
                    ev.partner_name, ev.recovery_value, ev.actor_id, ev.created_at
                )
                    ev.id::text AS id,
                    ev.old_status AS "oldStatus",
                    ev.new_status AS "newStatus",
                    ev.reason,
                    ev.document_reference AS "documentReference",
                    ev.partner_name AS "partnerName",
                    COALESCE(ev.recovery_value, 0) AS "recoveryValue",
                    ev.actor_id::text AS "actorId",
                    COALESCE(u.full_name, u.email) AS "actorName",
                    u.email AS "actorEmail",
                    r.code AS "actorRole",
                    ev.created_at AS "createdAt"
                FROM imei_disposition_events ev
                LEFT JOIN users u ON u.id = ev.actor_id
                LEFT JOIN roles r ON r.id = u.role_id
                WHERE ev.imei_id = :id OR ev.serial_id = :id
                ORDER BY
                    ev.old_status, ev.new_status, ev.reason, ev.document_reference,
                    ev.partner_name, ev.recovery_value, ev.actor_id, ev.created_at,
                    ev.id DESC
            ) deduplicated
            ORDER BY "createdAt" DESC, id DESC
            """
        ),
        {"id": identifier_id},
    )
    return [dict(row._mapping) for row in result]


@router.patch("/defective-identifiers/{identifier_id}/disposition", dependencies=[Depends(require_permission("after_sales:update"))])
async def update_disposition(
    identifier_id: UUID,
    payload: ImeiDispositionRequest,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from fastapi import HTTPException

    # 1. Try to find in product_imeis
    row = (await session.execute(
        text(
            """
            SELECT pi.id, pi.status, pi.product_id, pi.variant_id, pi.location_id,
                   pi.imei AS identifier, p.name AS product_name,
                   cost.on_hand_quantity, cost.average_unit_cost,
                   cost.location_code, cost.location_name,
                   'IMEI' AS type
            FROM product_imeis pi
            JOIN products p ON p.id = pi.product_id
            LEFT JOIN LATERAL (
                SELECT il.on_hand_quantity, il.average_unit_cost,
                       loc.code AS location_code, loc.name AS location_name
                FROM inventory_levels il
                LEFT JOIN inventory_locations loc ON loc.id = il.location_id
                WHERE il.variant_id IS NOT DISTINCT FROM pi.variant_id
                  AND (
                      il.product_id IS NOT DISTINCT FROM pi.product_id
                      OR (pi.variant_id IS NOT NULL AND il.product_id IS NULL)
                  )
                  AND (pi.location_id IS NULL OR il.location_id IS NOT DISTINCT FROM pi.location_id)
                ORDER BY
                    (pi.location_id IS NOT NULL AND il.location_id IS NOT DISTINCT FROM pi.location_id) DESC,
                    (COALESCE(il.average_unit_cost, 0) > 0) DESC,
                    il.updated_at DESC
                LIMIT 1
            ) cost ON TRUE
            WHERE pi.id=:id
            """
        ),
        {"id": identifier_id},
    )).first()

    if not row:
        # 2. Try to find in product_serial_numbers
        row = (await session.execute(
            text(
                """
                SELECT ps.id, ps.status, ps.product_id, ps.variant_id, ps.location_id,
                       ps.serial_number AS identifier, p.name AS product_name,
                       cost.on_hand_quantity, cost.average_unit_cost,
                       cost.location_code, cost.location_name,
                       'SERIAL' AS type
                FROM product_serial_numbers ps
                JOIN products p ON p.id = ps.product_id
                LEFT JOIN LATERAL (
                    SELECT il.on_hand_quantity, il.average_unit_cost,
                           loc.code AS location_code, loc.name AS location_name
                    FROM inventory_levels il
                    LEFT JOIN inventory_locations loc ON loc.id = il.location_id
                    WHERE il.variant_id IS NOT DISTINCT FROM ps.variant_id
                      AND (
                          il.product_id IS NOT DISTINCT FROM ps.product_id
                          OR (ps.variant_id IS NOT NULL AND il.product_id IS NULL)
                      )
                      AND (ps.location_id IS NULL OR il.location_id IS NOT DISTINCT FROM ps.location_id)
                    ORDER BY
                        (ps.location_id IS NOT NULL AND il.location_id IS NOT DISTINCT FROM ps.location_id) DESC,
                        (COALESCE(il.average_unit_cost, 0) > 0) DESC,
                        il.updated_at DESC
                    LIMIT 1
                ) cost ON TRUE
                WHERE ps.id=:id
                """
            ),
            {"id": identifier_id},
        )).first()

    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy mã định danh thiết bị lỗi.")

    new_status = payload.status.upper()

    # 3. Khóa cặp thiết bị trước, sau đó khóa toàn bộ IMEI/serial theo thứ tự ổn định.
    source_statuses = {
        "DEFECTIVE_RETURNED", "INSPECTION_PENDING", "RTV_PENDING", "LIQUIDATION_PENDING",
    }
    completed_statuses = {"REPAIRED", "RTV_COMPLETED", "LIQUIDATED", "SCRAP"}
    inventory_exit_statuses = {"RTV_COMPLETED", "LIQUIDATED", "SCRAP"}
    group = await lock_identifier_group(
        session,
        product_id=row.product_id,
        variant_id=row.variant_id,
        imei=row.identifier if row.type == "IMEI" else None,
        serial_number=row.identifier if row.type == "SERIAL" else None,
    )
    linked_identifiers = [
        {
            "id": identifier.id,
            "status": identifier.status,
            "identifier": identifier.value,
            "type": identifier.kind,
        }
        for identifier in group.identifiers
    ]
    selected = next((identifier for identifier in linked_identifiers if identifier["id"] == identifier_id), None)
    if not selected:
        raise HTTPException(status_code=409, detail="Mã định danh đã thay đổi trong lúc xử lý.")
    old_status = selected["status"]
    if all(linked["status"] == new_status for linked in linked_identifiers):
        return {"id": str(identifier_id), "status": new_status, "idempotent": True}
    linked_statuses = {linked["status"] for linked in linked_identifiers}
    if "REPAIR_PENDING" in linked_statuses:
        if linked_statuses != {"REPAIR_PENDING"}:
            raise HTTPException(status_code=409, detail="Nhóm IMEI/serial có trạng thái sửa chữa không đồng nhất.")
        source_statuses = {"REPAIR_PENDING"}
    elif new_status == "REPAIRED":
        raise HTTPException(status_code=409, detail="Chỉ có thể xác nhận sửa xong khi thiết bị đang chờ sửa chữa.")
    changed_identifiers = await update_locked_identifier_group_status(
        session,
        group=group,
        target_status=new_status,
        allowed_statuses=source_statuses,
    )

    # 6. Log adjustment log if entering terminal state
    terminal_reference_prefix = {
        "RTV_COMPLETED": "RTV",
        "LIQUIDATED": "LIQ",
        "SCRAP": "SCRAP",
        "OUT_OF_SYSTEM": "OUT",
    }
    if new_status in inventory_exit_statuses:
        reference_code = f"{terminal_reference_prefix[new_status]}-{row.identifier}"
        note_parts = [
            f"Định đoạt thiết bị lỗi ({row.type}) {row.identifier}: {old_status} -> {new_status}.",
            payload.reason,
        ]
        if payload.document_reference:
            note_parts.append(f"Chứng từ: {payload.document_reference}.")
        if payload.partner_name:
            note_parts.append(f"Đối tác: {payload.partner_name}.")
        if payload.recovery_value:
            note_parts.append(f"Giá trị thu hồi: {payload.recovery_value}.")
        await session.execute(
            text(
                """
                INSERT INTO inventory_adjustment_logs (
                    id, product_id, variant_id, old_quantity, new_quantity, delta,
                    transaction_type, reference_code, reason, note,
                    supplier_name, unit_cost, location_code, location_name
                )
                VALUES (
                    :id, :product_id, :variant_id, :old_quantity, :new_quantity, 0,
                    'ADJUSTMENT', :reference_code, :reason, :note,
                    :partner_name, :unit_cost, :location_code, :location_name
                )
                """
            ),
            {
                "id": uuid4(),
                "product_id": row.product_id,
                "variant_id": row.variant_id,
                "old_quantity": row.on_hand_quantity or 0,
                "new_quantity": row.on_hand_quantity or 0,
                "reference_code": reference_code,
                "reason": new_status,
                "note": " ".join(part for part in note_parts if part),
                "partner_name": payload.partner_name,
                "unit_cost": row.average_unit_cost,
                "location_code": row.location_code,
                "location_name": row.location_name,
            },
        )

    # 7. Ghi audit cho từng mã liên kết trong cùng một giao dịch.
    for linked in linked_identifiers:
        if linked["status"] == new_status:
            continue
        await session.execute(
            text(
                """
                INSERT INTO imei_disposition_events
                    (id, imei_id, serial_id, old_status, new_status, reason, document_reference,
                     partner_name, recovery_value, actor_id)
                VALUES (gen_random_uuid(), :imei_id, :serial_id, :old_status, :new_status, :reason,
                        :document, :partner, :value, :actor_id)
                """
            ),
            {
                "imei_id": linked["id"] if linked["type"] == "IMEI" else None,
                "serial_id": linked["id"] if linked["type"] == "SERIAL" else None,
                "old_status": linked["status"],
                "new_status": new_status,
                "reason": payload.reason,
                "document": payload.document_reference,
                "partner": payload.partner_name,
                "value": payload.recovery_value,
                "actor_id": actor_id,
            },
        )
    updated_count = len(changed_identifiers)
    await session.commit()
    return {
        "id": str(identifier_id),
        "status": new_status,
        "completed": new_status in completed_statuses,
        "updatedIdentifiers": updated_count,
    }


@router.post("/maintenance", dependencies=[Depends(require_permission("after_sales:update"))])
async def maintenance(session: AsyncSession = Depends(get_session)) -> dict:
    return await service.run_maintenance(session)
