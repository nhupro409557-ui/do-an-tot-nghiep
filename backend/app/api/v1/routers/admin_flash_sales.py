from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_permission
from app.api.v1.schemas.admin import FlashSalePayload
from app.application.services import flash_sale_service
from app.infrastructure.database.session import get_session

router = APIRouter()


@router.get("/flash-sales", dependencies=[Depends(require_permission("product:read"))])
async def list_flash_sales(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await flash_sale_service.list_flash_sales(session)


@router.post("/flash-sales", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("product:update"))])
async def create_flash_sale(payload: FlashSalePayload, session: AsyncSession = Depends(get_session)) -> dict:
    return await flash_sale_service.create_flash_sale(session, payload)


@router.patch("/flash-sales/{sale_id}", dependencies=[Depends(require_permission("product:update"))])
async def update_flash_sale(sale_id: UUID, payload: FlashSalePayload, session: AsyncSession = Depends(get_session)) -> dict:
    return await flash_sale_service.update_flash_sale(session, sale_id, payload)


@router.delete("/flash-sales/{sale_id}", dependencies=[Depends(require_permission("product:update"))])
async def delete_flash_sale(sale_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await flash_sale_service.delete_flash_sale(session, sale_id)
