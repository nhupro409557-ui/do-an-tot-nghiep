from uuid import UUID
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.application.services import payment_method_service
from app.infrastructure.database.session import get_session

router = APIRouter()


class UpdatePaymentMethodPayload(BaseModel):
    is_active: bool
    maintenance_message: str | None = Field(default=None, max_length=500)
    maintenance_starts_at: str | None = None
    maintenance_ends_at: str | None = None


@router.get("/payment-methods", dependencies=[Depends(require_permission("payment_method:read"))])
async def list_admin_payment_methods(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await payment_method_service.list_admin_payment_methods(session)


@router.patch("/payment-methods/{method_id}", dependencies=[Depends(require_permission("payment_method:update"))])
async def update_payment_method(
    method_id: UUID,
    payload: UpdatePaymentMethodPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await payment_method_service.update_payment_method(
        session=session,
        method_id=method_id,
        payload=payload.model_dump(),
    )
