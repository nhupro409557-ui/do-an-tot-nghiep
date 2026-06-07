from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.api.schemas.admin import VoucherPayload
from app.application.services import voucher_service
from app.infrastructure.database.session import get_session

router = APIRouter()


@router.get("/vouchers", dependencies=[Depends(require_permission("voucher:read"))])
async def list_admin_vouchers(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await voucher_service.list_admin_vouchers(session=session)


@router.post("/vouchers", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("voucher:create"))])
async def create_voucher(
    payload: VoucherPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await voucher_service.create_voucher(payload=payload, session=session)


@router.patch("/vouchers/{voucher_id}", dependencies=[Depends(require_permission("voucher:update"))])
async def update_voucher(
    voucher_id: UUID,
    payload: VoucherPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await voucher_service.update_voucher(voucher_id=voucher_id, payload=payload, session=session)


@router.delete("/vouchers/{voucher_id}", dependencies=[Depends(require_permission("voucher:delete"))])
async def deactivate_voucher(
    voucher_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await voucher_service.deactivate_voucher(voucher_id=voucher_id, session=session)
