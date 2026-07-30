from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_role_code, get_current_user_id, require_permission
from app.api.schemas.admin.purchase_order import PurchaseOrderPayload, PurchaseOrderStatusPayload
from app.application.services import purchase_order_service
from app.infrastructure.database.session import get_session


router = APIRouter()


@router.get("/purchase-orders", dependencies=[Depends(require_permission("inventory:view"))])
async def list_purchase_orders(
    search: str = Query(default="", max_length=120), status: str = Query(default="", max_length=30),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await purchase_order_service.list_purchase_orders(session, search, status)


@router.get("/purchase-orders/{order_id}", dependencies=[Depends(require_permission("inventory:view"))])
async def get_purchase_order(order_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await purchase_order_service.get_purchase_order(session, order_id)


@router.post("/purchase-orders", dependencies=[Depends(require_permission("inventory:adjust"))])
async def create_purchase_order(
    payload: PurchaseOrderPayload, session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await purchase_order_service.create_purchase_order(session, payload, current_user_id)


@router.put("/purchase-orders/{order_id}", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_purchase_order(
    order_id: UUID, payload: PurchaseOrderPayload, session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await purchase_order_service.update_purchase_order(session, order_id, payload, current_user_id)


@router.patch("/purchase-orders/{order_id}/status", dependencies=[Depends(require_permission("inventory:adjust"))])
async def update_purchase_order_status(
    order_id: UUID, payload: PurchaseOrderStatusPayload, session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id), current_role_code: str = Depends(get_current_role_code),
) -> dict:
    return await purchase_order_service.update_purchase_order_status(
        session, order_id, payload, current_user_id, current_role_code
    )
