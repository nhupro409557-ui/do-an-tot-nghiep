from uuid import UUID

from fastapi import APIRouter, Depends, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id, require_permission
from app.api.schemas.admin import (
    ContentPayload,
    AdminVideoCommentReplyPayload,
    AdminVideoCommentVisibilityPayload,
)
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session
from app.application.services import content_service


router = APIRouter()


@router.get("/content", dependencies=[Depends(require_permission("content:read"))])
async def list_admin_content(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await content_service.list_admin_content(session)


@router.post("/content", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("content:create"))])
async def create_content(
    payload: ContentPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.create_content(session, redis, payload, actor_id)


@router.patch("/content/{content_id}", dependencies=[Depends(require_permission("content:update"))])
async def update_content(
    content_id: UUID,
    payload: ContentPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.update_content(session, redis, content_id, payload, actor_id)


@router.delete("/content/{content_id}", dependencies=[Depends(require_permission("content:delete"))])
async def delete_content(
    content_id: UUID,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.delete_content(session, redis, content_id, actor_id)


@router.get("/banners", dependencies=[Depends(require_permission("content:read"))])
async def list_admin_banners(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await content_service.list_admin_banners(session)


@router.post("/banners", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("content:create"))])
async def create_banner(
    payload: ContentPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.create_banner(session, redis, payload, actor_id)


@router.patch("/banners/{banner_id}", dependencies=[Depends(require_permission("content:update"))])
async def update_banner(
    banner_id: UUID,
    payload: ContentPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.update_banner(session, redis, banner_id, payload, actor_id)


@router.delete("/banners/{banner_id}", dependencies=[Depends(require_permission("content:delete"))])
async def delete_banner(
    banner_id: UUID,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.delete_banner(session, redis, banner_id, actor_id)


@router.get("/videos", dependencies=[Depends(require_permission("content:read"))])
async def list_admin_videos(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await content_service.list_admin_videos(session)


@router.post("/videos", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("content:create"))])
async def create_admin_video(
    payload: ContentPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.create_admin_video(session, redis, payload, actor_id)


@router.patch("/videos/{video_id}", dependencies=[Depends(require_permission("content:update"))])
async def update_admin_video(
    video_id: UUID,
    payload: ContentPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.update_admin_video(session, redis, video_id, payload, actor_id)


@router.delete("/videos/{video_id}", dependencies=[Depends(require_permission("content:delete"))])
async def delete_admin_video(
    video_id: UUID,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.delete_admin_video(session, redis, video_id, actor_id)


@router.post("/videos/{video_id}/comments/{comment_id}/reply", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("content:update"))])
async def reply_admin_video_comment(
    video_id: UUID,
    comment_id: UUID,
    payload: AdminVideoCommentReplyPayload,
    session: AsyncSession = Depends(get_session),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.reply_admin_video_comment(session, video_id, comment_id, payload, actor_id)


@router.patch("/videos/{video_id}/comments/{comment_id}", dependencies=[Depends(require_permission("content:update"))])
async def update_admin_video_comment(
    video_id: UUID,
    comment_id: UUID,
    payload: AdminVideoCommentVisibilityPayload,
    session: AsyncSession = Depends(get_session),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.update_admin_video_comment(session, video_id, comment_id, payload, actor_id)


@router.get("/image-comments", dependencies=[Depends(require_permission("review:read"))])
async def list_admin_image_comments(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await content_service.list_admin_image_comments(session)


@router.post("/image-comments/{comment_id}/reply", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("review:update"))])
async def reply_admin_image_comment(
    comment_id: UUID,
    payload: AdminVideoCommentReplyPayload,
    session: AsyncSession = Depends(get_session),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.reply_admin_image_comment(session, comment_id, payload, actor_id)


@router.patch("/image-comments/{comment_id}", dependencies=[Depends(require_permission("review:update"))])
async def update_admin_image_comment(
    comment_id: UUID,
    payload: AdminVideoCommentVisibilityPayload,
    session: AsyncSession = Depends(get_session),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await content_service.update_admin_image_comment(session, comment_id, payload, actor_id)
