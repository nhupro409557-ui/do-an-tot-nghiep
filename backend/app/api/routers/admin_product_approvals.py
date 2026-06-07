from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_role_code, require_permission
from app.api.schemas.admin import ProductBulkActionPayload
from app.application.services import product_approval_service
from app.infrastructure.database.session import get_session


router = APIRouter()


@router.post("/products/{product_id}/submit", dependencies=[Depends(require_permission("product:update"))])
async def submit_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await product_approval_service.submit_product(product_id=product_id, session=session)


@router.post("/products/{product_id}/approve", dependencies=[Depends(require_permission("product:update"))])
async def approve_product(
    product_id: UUID,
    session: AsyncSession = Depends(get_session),
    role_code: str = Depends(get_current_role_code),
) -> dict:
    return await product_approval_service.approve_product(product_id=product_id, session=session, role_code=role_code)


@router.post("/products/{product_id}/reactivate", dependencies=[Depends(require_permission("product:update"))])
async def reactivate_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await product_approval_service.reactivate_product(product_id=product_id, session=session)


@router.post("/products/{product_id}/hide", dependencies=[Depends(require_permission("product:update"))])
async def hide_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await product_approval_service.hide_product(product_id=product_id, session=session)


@router.post("/products/bulk-approve", dependencies=[Depends(require_permission("product:update"))])
async def bulk_approve_products(
    payload: ProductBulkActionPayload,
    session: AsyncSession = Depends(get_session),
    role_code: str = Depends(get_current_role_code),
) -> dict:
    return await product_approval_service.bulk_approve_products(payload=payload, session=session, role_code=role_code)


@router.post("/products/bulk-action", dependencies=[Depends(require_permission("product:update"))])
async def product_bulk_action(
    payload: ProductBulkActionPayload,
    session: AsyncSession = Depends(get_session),
    role_code: str = Depends(get_current_role_code),
) -> dict:
    return await product_approval_service.product_bulk_action(payload=payload, session=session, role_code=role_code)


@router.post("/products/{product_id}/archive", dependencies=[Depends(require_permission("product:update"))])
async def archive_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await product_approval_service.archive_product(product_id=product_id, session=session)


@router.delete("/products/{product_id}", dependencies=[Depends(require_permission("product:delete"))])
async def deactivate_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await product_approval_service.deactivate_product(product_id=product_id, session=session)
