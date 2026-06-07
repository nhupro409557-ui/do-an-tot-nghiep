from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id
from app.api.routers.catalog_utils import CreateProductRequest, ProductAnalyticsEventRequest
from app.application.services import catalog_product_service
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session


router = APIRouter()


@router.get("/products/{product_id}")
async def get_product(product_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    return await catalog_product_service.get_product(product_id, session)


@router.post("/products/{product_id}/view", status_code=status.HTTP_201_CREATED)
async def record_product_view_heartbeat(
    product_id: str,
    payload: ProductAnalyticsEventRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    return await catalog_product_service.record_product_view_heartbeat(product_id, payload, request, session, redis)


@router.post("/products/{product_id}/favorite", status_code=status.HTTP_200_OK)
async def toggle_favorite(
    product_id: UUID,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await catalog_product_service.toggle_favorite(product_id, session, redis, current_user_id)


@router.get("/favorites", status_code=status.HTTP_200_OK)
async def list_favorites(
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> list[dict]:
    return await catalog_product_service.list_favorites(session, current_user_id)


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(payload: CreateProductRequest, session: AsyncSession = Depends(get_session)) -> dict:
    return await catalog_product_service.create_product(payload, session)
