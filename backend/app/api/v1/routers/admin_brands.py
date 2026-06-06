from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id, require_permission
from app.api.v1.schemas.admin import (
    BrandBulkStatusPayload,
    BrandCodeCheckPayload,
    BrandPayload,
    BrandStatusPayload,
)
from app.application.services import brand_service
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session

router = APIRouter()


@router.get("/brands", dependencies=[Depends(require_permission("brand:read"))])
async def list_admin_brands(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=120),
    status_filter: str = Query(default="all", alias="status"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await brand_service.list_admin_brands(
        session=session,
        page=page,
        limit=limit,
        search=search,
        status_filter=status_filter,
    )


@router.post("/brands/check-code", dependencies=[Depends(require_permission("brand:read"))])
async def check_brand_code(
    payload: BrandCodeCheckPayload,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await brand_service.check_brand_code(payload=payload, session=session)


@router.post("/brands", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("brand:create"))])
async def create_brand(
    payload: BrandPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    return await brand_service.create_brand(payload=payload, session=session, redis=redis)


@router.patch("/brands/{brand_id}", dependencies=[Depends(require_permission("brand:update"))])
async def update_brand(
    brand_id: UUID,
    payload: BrandPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await brand_service.update_brand(
        brand_id=brand_id,
        payload=payload,
        session=session,
        redis=redis,
        current_user_id=current_user_id,
    )


@router.post("/brands/import", dependencies=[Depends(require_permission("brand:create"))])
async def import_brands(
    mode: str = Form(default="skip"),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await brand_service.import_brands(
        mode=mode,
        file=file,
        session=session,
        redis=redis,
        current_user_id=current_user_id,
    )


@router.get("/brands/import-jobs", dependencies=[Depends(require_permission("brand:read"))])
async def list_brand_import_jobs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await brand_service.list_brand_import_jobs(session=session)


@router.get("/brands/import-jobs/{job_id}", dependencies=[Depends(require_permission("brand:read"))])
async def get_brand_import_job(
    job_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    forwarded = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return await brand_service.get_brand_import_job(
        job_id=job_id,
        client_ip=client_ip,
        session=session,
        redis=redis,
    )


@router.patch("/brands/{brand_id}/status", dependencies=[Depends(require_permission("brand:update"))])
async def update_brand_status(
    brand_id: UUID,
    payload: BrandStatusPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await brand_service.update_brand_status(
        brand_id=brand_id,
        payload=payload,
        background_tasks=background_tasks,
        session=session,
        redis=redis,
        current_user_id=current_user_id,
    )


@router.patch("/brands/status", dependencies=[Depends(require_permission("brand:update"))])
async def update_brands_status(
    payload: BrandBulkStatusPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await brand_service.update_brands_status(
        payload=payload,
        session=session,
        redis=redis,
        current_user_id=current_user_id,
    )


@router.get("/brands/status-jobs", dependencies=[Depends(require_permission("brand:read"))])
async def list_brand_status_jobs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await brand_service.list_brand_status_jobs(session=session)


@router.delete("/brands/{brand_id}", dependencies=[Depends(require_permission("brand:delete"))])
async def deactivate_brand(
    brand_id: UUID,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await brand_service.deactivate_brand(
        brand_id=brand_id,
        session=session,
        redis=redis,
        current_user_id=current_user_id,
    )
