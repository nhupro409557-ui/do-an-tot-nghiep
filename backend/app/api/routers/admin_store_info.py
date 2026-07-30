from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
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


class UpdateStorePolicyPayload(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    content: str = Field(min_length=1, max_length=5000)
    is_active: bool = True


@router.get("/store-info/policies", dependencies=[Depends(require_permission("store_info:read"))])
async def list_store_policies(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await store_info_service.list_store_policies(session)


@router.patch("/store-info/policies/{code}", dependencies=[Depends(require_permission("store_info:update"))])
async def update_store_policy(
    code: str,
    payload: UpdateStorePolicyPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await store_info_service.update_store_policy(
        session=session,
        code=code,
        payload=payload.model_dump(),
    )



@router.patch("/store-info", dependencies=[Depends(require_permission("store_info:update"))])
async def update_store_info(
    payload: UpdateStoreInfoPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await store_info_service.update_store_info(
        session=session,
        payload=payload.model_dump(),
    )
