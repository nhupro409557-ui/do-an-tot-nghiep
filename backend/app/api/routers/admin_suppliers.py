from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id, require_permission
from app.api.schemas.admin import (
    SupplierBulkStatusPayload,
    SupplierCodeCheckPayload,
    SupplierPayload,
    SupplierStatusPayload,
)
from app.application.services import supplier_service
from app.infrastructure.database.session import get_session

router = APIRouter()


@router.get("/suppliers", dependencies=[Depends(require_permission("supplier:read"))])
async def list_admin_suppliers(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=120),
    status_filter: str = Query(default="all", alias="status"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await supplier_service.list_admin_suppliers(
        session=session,
        page=page,
        limit=limit,
        search=search,
        status_filter=status_filter,
    )


@router.post("/suppliers/check-code", dependencies=[Depends(require_permission("supplier:read"))])
async def check_supplier_code(
    payload: SupplierCodeCheckPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await supplier_service.check_supplier_code(payload=payload, session=session)


@router.post("/suppliers", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("supplier:create"))])
async def create_supplier(
    payload: SupplierPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await supplier_service.create_supplier(payload=payload, session=session, current_user_id=current_user_id)


@router.patch("/suppliers/{supplier_id}", dependencies=[Depends(require_permission("supplier:update"))])
async def update_supplier(
    supplier_id: UUID,
    payload: SupplierPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await supplier_service.update_supplier(
        supplier_id=supplier_id,
        payload=payload,
        session=session,
        current_user_id=current_user_id,
    )


@router.patch("/suppliers/{supplier_id}/status", dependencies=[Depends(require_permission("supplier:update"))])
async def update_supplier_status(
    supplier_id: UUID,
    payload: SupplierStatusPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await supplier_service.update_supplier_status(
        supplier_id=supplier_id,
        payload=payload,
        session=session,
        current_user_id=current_user_id,
    )


@router.patch("/suppliers/status", dependencies=[Depends(require_permission("supplier:update"))])
async def update_suppliers_status(
    payload: SupplierBulkStatusPayload,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await supplier_service.update_suppliers_status(
        payload=payload,
        session=session,
        current_user_id=current_user_id,
    )


@router.delete("/suppliers/{supplier_id}", dependencies=[Depends(require_permission("supplier:delete"))])
async def delete_supplier(
    supplier_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await supplier_service.delete_supplier(
        supplier_id=supplier_id,
        session=session,
        current_user_id=current_user_id,
    )
