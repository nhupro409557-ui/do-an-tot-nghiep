from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id
from app.api.v1.schemas.content import (
    ProductImageCommentRequest,
    ReviewRequest,
    ReviewUpdateRequest,
    VideoCommentRequest,
    VideoViewHeartbeatRequest,
)
from app.application.services import public_content_service
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session


router = APIRouter(tags=["Content"])


@router.get("/products/{product_id}/reviews")
async def list_reviews(product_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await public_content_service.list_reviews(product_id, session)


@router.get("/products/{product_id}/reviews/eligibility")
async def review_eligibility(
    product_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await public_content_service.get_review_eligibility(product_id, current_user_id, session)


@router.post("/products/{product_id}/reviews", status_code=status.HTTP_201_CREATED)
async def create_review(
    product_id: UUID,
    payload: ReviewRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await public_content_service.create_review(product_id, payload, current_user_id, session)


@router.patch("/products/{product_id}/reviews/{review_id}")
async def update_own_review(
    product_id: UUID,
    review_id: UUID,
    payload: ReviewUpdateRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await public_content_service.update_own_review(product_id, review_id, payload, current_user_id, session)


@router.delete("/products/{product_id}/reviews/{review_id}")
async def delete_own_review(
    product_id: UUID,
    review_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await public_content_service.delete_own_review(product_id, review_id, current_user_id, session)


@router.get("/notifications")
async def list_notifications(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await public_content_service.list_notifications(current_user_id, session)


@router.patch("/notifications/read-all")
async def mark_notifications_read(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    return await public_content_service.mark_notifications_read(current_user_id, session)


@router.get("/rewards")
async def list_rewards(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await public_content_service.list_rewards(session)


@router.get("/banners")
async def list_banners(
    limit: int = Query(default=8, ge=1, le=12),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> list[dict]:
    return await public_content_service.list_banners(limit, session, redis)


@router.get("/videos")
async def list_videos(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=48),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    return await public_content_service.list_videos(page, limit, session, redis)


@router.post("/videos/{video_id}/view")
async def record_video_view(
    video_id: UUID,
    payload: VideoViewHeartbeatRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    x_device_id: str | None = Header(default=None),
) -> dict:
    fingerprint = x_device_id or f"{request.client.host if request.client else 'unknown'}:{request.headers.get('user-agent', '')[:120]}"
    return await public_content_service.record_video_view(video_id, payload, fingerprint, session, redis)


@router.post("/videos/{video_id}/like")
async def toggle_video_like(
    video_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await public_content_service.toggle_video_like(video_id, session, current_user_id)


@router.post("/videos/{video_id}/comments", status_code=status.HTTP_201_CREATED)
async def create_video_comment(
    video_id: UUID,
    payload: VideoCommentRequest,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await public_content_service.create_video_comment(video_id, payload, session, current_user_id)


@router.delete("/videos/{video_id}/comments/{comment_id}")
async def retract_video_comment(
    video_id: UUID,
    comment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await public_content_service.retract_video_comment(video_id, comment_id, session, current_user_id)


@router.get("/products/{product_id}/image-comments")
async def list_product_image_comments(product_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await public_content_service.list_product_image_comments(product_id, session)


@router.post("/products/{product_id}/image-comments", status_code=status.HTTP_201_CREATED)
async def create_product_image_comment(
    product_id: UUID,
    payload: ProductImageCommentRequest,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await public_content_service.create_product_image_comment(product_id, payload, session, current_user_id)


@router.delete("/products/{product_id}/image-comments/{comment_id}")
async def retract_product_image_comment(
    product_id: UUID,
    comment_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    return await public_content_service.retract_product_image_comment(product_id, comment_id, session, current_user_id)
