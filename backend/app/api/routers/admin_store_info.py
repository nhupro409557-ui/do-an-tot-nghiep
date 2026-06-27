from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_staff_or_admin
from app.application.services import store_info_service
from app.infrastructure.database.session import get_session

router = APIRouter()


class UpdateStoreInfoPayload(BaseModel):
    name: str = Field(max_length=100)
    hotline: str = Field(max_length=50)
    email: str = Field(max_length=100)
    address: str = Field(max_length=500)

    description: str
    lat: float | None = None
    lng: float | None = None



@router.patch("/store-info", dependencies=[Depends(require_staff_or_admin)])
async def update_store_info(
    payload: UpdateStoreInfoPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await store_info_service.update_store_info(
        session=session,
        payload=payload.model_dump(),
    )
