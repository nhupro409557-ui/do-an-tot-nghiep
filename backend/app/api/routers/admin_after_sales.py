from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id, require_staff_or_admin
from app.application.after_sales import service
from app.application.after_sales.schemas import ImeiDispositionRequest, UpdateAfterSalesStatusRequest
from app.infrastructure.database.session import get_session


router = APIRouter(
    prefix="/after-sales",
    tags=["Admin - Hậu mãi"],
    dependencies=[Depends(require_staff_or_admin)],
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


@router.patch("/returns/{request_id}/status")
async def update_return(
    request_id: UUID,
    payload: UpdateAfterSalesStatusRequest,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.admin_update_status(
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


@router.patch("/warranties/{request_id}/status")
async def update_warranty(
    request_id: UUID,
    payload: UpdateAfterSalesStatusRequest,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await service.admin_update_status(
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
                   p.name AS "productName", pi.received_at AS "receivedAt",
                   il.average_unit_cost AS "averageUnitCost"
            FROM product_imeis pi
            JOIN products p ON p.id=pi.product_id
            LEFT JOIN inventory_levels il ON il.variant_id IS NOT DISTINCT FROM pi.variant_id
            WHERE pi.status IN (
                'DEFECTIVE_RETURNED','INSPECTION_PENDING','RTV_PENDING',
                'LIQUIDATION_PENDING','RTV_COMPLETED','LIQUIDATED','SCRAP','OUT_OF_SYSTEM'
            ) AND (CAST(:status AS VARCHAR) IS NULL OR pi.status=CAST(:status AS VARCHAR))
            ORDER BY pi.updated_at DESC
            """
        ),
        {"status": status_value},
    )
    return [dict(row._mapping) for row in result]


@router.patch("/defective-identifiers/{identifier_id}/disposition")
async def update_disposition(
    identifier_id: UUID,
    payload: ImeiDispositionRequest,
    actor_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    row = (await session.execute(
        text("SELECT id, status FROM product_imeis WHERE id=:id FOR UPDATE"),
        {"id": identifier_id},
    )).first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Không tìm thấy IMEI.")
    terminal_sources = {"RTV_COMPLETED", "LIQUIDATED", "SCRAP"}
    if payload.status == "OUT_OF_SYSTEM" and row.status not in terminal_sources:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="IMEI phải hoàn tất RTV, thanh lý hoặc phế phẩm trước khi xuất khỏi hệ thống.")
    await session.execute(
        text("UPDATE product_imeis SET status=:status, updated_at=NOW() WHERE id=:id"),
        {"status": payload.status, "id": identifier_id},
    )
    await session.execute(
        text(
            """
            INSERT INTO imei_disposition_events
                (id, imei_id, old_status, new_status, reason, document_reference,
                 partner_name, recovery_value, actor_id)
            VALUES (gen_random_uuid(), :imei_id, :old_status, :new_status, :reason,
                    :document, :partner, :value, :actor_id)
            """
        ),
        {
            "imei_id": identifier_id, "old_status": row.status, "new_status": payload.status,
            "reason": payload.reason, "document": payload.document_reference,
            "partner": payload.partner_name, "value": payload.recovery_value, "actor_id": actor_id,
        },
    )
    await session.commit()
    return {"id": str(identifier_id), "status": payload.status}


@router.post("/maintenance")
async def maintenance(session: AsyncSession = Depends(get_session)) -> dict:
    return await service.run_maintenance(session)
