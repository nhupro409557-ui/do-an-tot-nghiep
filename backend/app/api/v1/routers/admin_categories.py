from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id, require_permission
from app.api.v1.schemas.admin import (
    CategoryBulkPayload,
    CategoryPayload,
    CategoryReorderPayload,
    CategorySlugCheckPayload,
)
from app.application.services import category_service
from app.application.services.category_service import audit_product_event, ensure_categories_not_migrating
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session


router = APIRouter()


@router.get("/categories", dependencies=[Depends(require_permission("category:read"))])
async def list_admin_categories(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await category_service.list_admin_categories(session=session)


@router.post("/categories/check-slug", dependencies=[Depends(require_permission("category:read"))])
async def check_category_slug(payload: CategorySlugCheckPayload, session: AsyncSession = Depends(get_session)) -> dict:
    return await category_service.check_category_slug(payload=payload, session=session)


@router.post("/categories", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("category:create"))])
async def create_category(
    payload: CategoryPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await category_service.create_category(
        payload=payload,
        background_tasks=background_tasks,
        session=session,
        redis=redis,
        actor_id=actor_id,
    )


@router.patch("/categories/reorder", dependencies=[Depends(require_permission("category:update"))])
async def reorder_categories(
    payload: CategoryReorderPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await category_service.reorder_categories(
        payload=payload,
        background_tasks=background_tasks,
        session=session,
        redis=redis,
        actor_id=actor_id,
    )


@router.put("/categories/bulk", dependencies=[Depends(require_permission("category:update"))])
async def bulk_update_categories(
    payload: CategoryBulkPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await category_service.bulk_update_categories(
        payload=payload,
        background_tasks=background_tasks,
        session=session,
        redis=redis,
        actor_id=actor_id,
    )


@router.patch("/categories/{category_id}", dependencies=[Depends(require_permission("category:update"))])
async def update_category(
    category_id: UUID,
    payload: CategoryPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await category_service.update_category(
        category_id=category_id,
        payload=payload,
        background_tasks=background_tasks,
        session=session,
        redis=redis,
        actor_id=actor_id,
    )


@router.patch("/categories/{category_id}/restore", dependencies=[Depends(require_permission("category:update"))])
async def restore_category(
    category_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await category_service.restore_category(
        category_id=category_id,
        background_tasks=background_tasks,
        session=session,
        redis=redis,
        actor_id=actor_id,
    )


@router.delete("/categories/{category_id}", dependencies=[Depends(require_permission("category:delete"))])
async def deactivate_category(
    category_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await category_service.deactivate_category(
        category_id=category_id,
        background_tasks=background_tasks,
        session=session,
        redis=redis,
        actor_id=actor_id,
    )


@router.get("/categories/{category_id}/audit-logs", dependencies=[Depends(require_permission("category:read"))])
async def list_category_audit_logs(category_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await category_service.list_category_audit_logs(category_id=category_id, session=session)


@router.get("/categories/{category_id}/migration-jobs", dependencies=[Depends(require_permission("category:read"))])
async def list_category_migration_jobs(category_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await category_service.list_category_migration_jobs(category_id=category_id, session=session)


@router.get("/categories/ops/metrics", dependencies=[Depends(require_permission("category:read"))])
async def category_operational_metrics(session: AsyncSession = Depends(get_session), redis: Redis = Depends(get_redis)) -> dict:
    return await category_service.category_operational_metrics(session=session, redis=redis)
