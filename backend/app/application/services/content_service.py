import json
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import (
    ContentPayload,
    ContentCommentPayload,
    AdminVideoCommentReplyPayload,
    AdminVideoCommentVisibilityPayload,
)
from app.infrastructure.database.repositories import (
    admin_content_repo,
    content_comment_repo,
    public_content_repo,
)
from app.shared.admin_utils import ensure_not_data_url
from app.shared.reviews import sanitize_review_text


def normalize_content_type(value: str | None) -> str:
    candidate = (value or "VIDEO").strip().upper()
    return candidate if candidate in {"VIDEO", "BANNER", "MARKETING_PAGE"} else "VIDEO"


def normalize_content_status(
    value: str | None,
    *,
    scheduled_at: datetime | None,
    published_at: datetime | None,
    is_active: bool,
) -> str:
    candidate = (value or "").strip().upper()
    allowed = {"DRAFT", "SCHEDULED", "PUBLISHED", "ARCHIVED"}
    if candidate not in allowed:
        if not is_active:
            return "ARCHIVED"
        if scheduled_at and scheduled_at > datetime.now(timezone.utc):
            return "SCHEDULED"
        if published_at or is_active:
            return "PUBLISHED"
        return "DRAFT"
    return candidate


def parse_optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def normalize_content_comments(comments: list[ContentCommentPayload]) -> list[dict]:
    normalized: list[dict] = []
    for item in comments:
        normalized.append(
            {
                "id": item.id or uuid4().hex[:12],
                "userName": item.userName.strip(),
                "content": sanitize_review_text(item.content).strip(),
                "parentId": item.parentId,
                "isHidden": bool(item.isHidden),
            }
        )
    return normalized


def normalize_video_source(value: str | None) -> str:
    normalized = (value or "UPLOAD").strip().upper()
    if normalized not in {"UPLOAD", "YOUTUBE"}:
        raise HTTPException(status_code=422, detail="videoSource must be UPLOAD or YOUTUBE.")
    return normalized


def normalize_video_category(value: str | None) -> str:
    normalized = (value or "PRODUCT").strip().upper()
    allowed = {"PRODUCT", "NEWS", "TIPS", "SERVICE", "REVIEW", "OTHER"}
    if normalized not in allowed:
        raise HTTPException(status_code=422, detail="Invalid videoCategory.")
    return normalized


def is_youtube_url(value: str | None) -> bool:
    if not value:
        return False
    return bool(re.search(r"(youtube\.com/(watch\?.*v=|embed/|shorts/|live/)|youtu\.be/)", value.strip(), re.I))


def validate_content_payload(payload: ContentPayload) -> dict:
    content_type = normalize_content_type(payload.contentType)
    video_source = normalize_video_source(payload.videoSource)
    video_category = normalize_video_category(payload.videoCategory)
    video_url = payload.videoUrl.strip() if payload.videoUrl else None
    thumbnail_url = payload.thumbnailUrl.strip() if payload.thumbnailUrl else None
    banner_image_url = payload.bannerImageUrl.strip() if payload.bannerImageUrl else None
    cta_url = payload.ctaUrl.strip() if payload.ctaUrl else None
    ensure_not_data_url(video_url, "videoUrl")
    ensure_not_data_url(thumbnail_url, "thumbnailUrl")
    ensure_not_data_url(banner_image_url, "bannerImageUrl")
    ensure_not_data_url(cta_url, "ctaUrl")
    scheduled_at = parse_optional_datetime(payload.scheduledAt)
    published_at = parse_optional_datetime(payload.publishedAt)
    now_utc = datetime.now(timezone.utc)
    if content_type == "VIDEO" and not video_url:
        raise HTTPException(status_code=422, detail="Video content requires videoUrl.")
    if content_type == "BANNER" and not (banner_image_url or thumbnail_url):
        raise HTTPException(status_code=422, detail="Banner content requires bannerImageUrl or thumbnailUrl.")
    if video_url and video_source == "UPLOAD" and not any(str(video_url).lower().split("?")[0].endswith(ext) for ext in (".mp4", ".webm")):
        raise HTTPException(status_code=422, detail="videoUrl must use mp4 or webm.")
    if video_url and video_source == "YOUTUBE" and not is_youtube_url(video_url):
        raise HTTPException(status_code=422, detail="videoUrl must be a YouTube link.")
    if scheduled_at and scheduled_at < now_utc + timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="scheduledAt must be at least 5 minutes in the future.")
    if scheduled_at and published_at and published_at < scheduled_at:
        raise HTTPException(status_code=422, detail="publishedAt must not be earlier than scheduledAt.")
    status_value = normalize_content_status(payload.status, scheduled_at=scheduled_at, published_at=published_at, is_active=payload.isActive)
    comments = normalize_content_comments(payload.comments)
    return {
        "title": payload.title.strip(),
        "description": payload.description.strip(),
        "content_type": content_type,
        "video_source": video_source,
        "video_category": video_category,
        "status": status_value,
        "video_url": video_url,
        "thumbnail_url": thumbnail_url,
        "banner_image_url": banner_image_url,
        "content_body": payload.contentBody.strip(),
        "cta_label": payload.ctaLabel.strip() if payload.ctaLabel else None,
        "cta_url": cta_url,
        "product_ids": [item for item in payload.productIds if item],
        "category_ids": [item for item in payload.categoryIds if item],
        "comments": comments,
        "like_count": 0,
        "view_count": 0,
        "sort_order": payload.sortOrder,
        "scheduled_at": scheduled_at,
        "published_at": published_at,
        "is_active": payload.isActive,
        "version": payload.version,
    }


def content_storefront_cache_key(page: int, limit: int) -> str:
    return f"storefront:content:videos:page:{page}:limit:{limit}"


async def invalidate_content_storefront_cache(redis: Redis, max_pages: int = 12, page_sizes: tuple[int, ...] = (12, 24, 48)) -> None:
    tracked_key = "storefront:content:videos:keys"
    try:
        tracked = await redis.smembers(tracked_key)
        if tracked:
            await redis.delete(*list(tracked))
        await redis.delete(tracked_key)
    except Exception:
        return


async def replace_content_product_relations(session: AsyncSession, content_id: UUID, product_ids: list[str]) -> None:
    await admin_content_repo.delete_content_product_relations(session, content_id)
    for product_id in product_ids:
        await admin_content_repo.insert_content_product_relation(session, content_id, product_id)


async def replace_content_category_relations(session: AsyncSession, content_id: UUID, category_ids: list[str]) -> None:
    await admin_content_repo.delete_content_category_relations(session, content_id)
    for category_id in category_ids:
        await admin_content_repo.insert_content_category_relation(session, content_id, category_id)


async def replace_content_comments(session: AsyncSession, content_id: UUID, comments: list[dict], actor_id: UUID) -> None:
    await content_comment_repo.delete_content_comments(session, content_id)
    for item in comments:
        comment_id = item.get("id")
        try:
            persisted_id = UUID(str(comment_id))
        except Exception:
            persisted_id = uuid4()
        parent_id = item.get("parentId")
        try:
            parent_uuid = UUID(str(parent_id)) if parent_id else None
        except Exception:
            parent_uuid = None
        await content_comment_repo.insert_admin_content_comment(
            session,
            id=persisted_id,
            content_id=content_id,
            user_name=item["userName"],
            body=item["content"],
            parent_id=parent_uuid,
            is_hidden=item["isHidden"],
            created_by=actor_id,
            updated_by=actor_id,
        )


async def list_admin_content(session: AsyncSession) -> list[dict]:
    return await admin_content_repo.list_admin_content(session)


async def create_content(
    session: AsyncSession, redis: Redis, payload: ContentPayload, actor_id: UUID
) -> dict:
    data = validate_content_payload(payload)
    content_id = uuid4()
    await admin_content_repo.insert_content_record(session, id=content_id, created_by=actor_id, updated_by=actor_id, data=data)
    await replace_content_product_relations(session, content_id, data["product_ids"])
    await replace_content_category_relations(session, content_id, data["category_ids"])
    await replace_content_comments(session, content_id, data["comments"], actor_id)
    await admin_content_repo.audit_admin_event(session, actor_id=actor_id, event_type="content_created", resource="content", metadata={"contentId": str(content_id), "contentType": data["content_type"], "videoCategory": data["video_category"], "status": data["status"]})
    await session.commit()
    await invalidate_content_storefront_cache(redis)
    return {"id": str(content_id)}


async def update_content(
    session: AsyncSession, redis: Redis, content_id: UUID, payload: ContentPayload, actor_id: UUID
) -> dict:
    data = validate_content_payload(payload)
    expected_version = data.get("version")
    if expected_version is None:
        raise HTTPException(status_code=409, detail="Missing content version. Reload before saving.")
    
    updated_count = await admin_content_repo.update_content_record(
        session, id=content_id, updated_by=actor_id, expected_version=expected_version, data=data
    )
    if updated_count == 0:
        exists = await admin_content_repo.check_content_exists(session, content_id)
        if exists:
            raise HTTPException(status_code=409, detail="Content was updated by another admin. Reload before saving.")
        raise HTTPException(status_code=404, detail="Content not found.")
        
    await replace_content_product_relations(session, content_id, data["product_ids"])
    await replace_content_category_relations(session, content_id, data["category_ids"])
    await replace_content_comments(session, content_id, data["comments"], actor_id)
    await admin_content_repo.audit_admin_event(session, actor_id=actor_id, event_type="content_updated", resource="content", metadata={"contentId": str(content_id), "contentType": data["content_type"], "videoCategory": data["video_category"], "status": data["status"]})
    await session.commit()
    await invalidate_content_storefront_cache(redis)
    return {"ok": True}


async def delete_content(
    session: AsyncSession, redis: Redis, content_id: UUID, actor_id: UUID
) -> dict:
    updated_count = await admin_content_repo.soft_delete_content_record(session, id=content_id, actor_id=actor_id)
    if updated_count == 0:
        raise HTTPException(status_code=404, detail="Content not found.")
    await admin_content_repo.audit_admin_event(session, actor_id=actor_id, event_type="content_deleted", resource="content", metadata={"contentId": str(content_id), "mode": "soft_delete"})
    await session.commit()
    await invalidate_content_storefront_cache(redis)
    return {"ok": True}


def prepare_banner_payload(payload: ContentPayload) -> ContentPayload:
    if not payload.categoryIds:
        raise HTTPException(status_code=422, detail="Banner phải chọn ít nhất một danh mục.")
    payload.contentType = "BANNER"
    payload.videoUrl = None
    payload.thumbnailUrl = payload.thumbnailUrl or payload.bannerImageUrl
    payload.bannerImageUrl = payload.bannerImageUrl or payload.thumbnailUrl
    payload.videoSource = "UPLOAD"
    payload.videoCategory = "OTHER"
    payload.comments = []
    if payload.productIds:
        payload.productIds = payload.productIds[:1]
    return payload


async def list_admin_banners(session: AsyncSession) -> list[dict]:
    items = await list_admin_content(session)
    return [item for item in items if item.get("contentType") == "BANNER"]


async def create_banner(
    session: AsyncSession, redis: Redis, payload: ContentPayload, actor_id: UUID
) -> dict:
    return await create_content(session, redis, prepare_banner_payload(payload), actor_id)


async def update_banner(
    session: AsyncSession, redis: Redis, banner_id: UUID, payload: ContentPayload, actor_id: UUID
) -> dict:
    return await update_content(session, redis, banner_id, prepare_banner_payload(payload), actor_id)


async def delete_banner(
    session: AsyncSession, redis: Redis, banner_id: UUID, actor_id: UUID
) -> dict:
    return await delete_content(session, redis, banner_id, actor_id)


async def list_admin_videos(session: AsyncSession) -> list[dict]:
    items = await list_admin_content(session)
    return [item for item in items if item.get("contentType") == "VIDEO"]


async def create_admin_video(
    session: AsyncSession, redis: Redis, payload: ContentPayload, actor_id: UUID
) -> dict:
    payload.contentType = "VIDEO"
    return await create_content(session, redis, payload, actor_id)


async def update_admin_video(
    session: AsyncSession, redis: Redis, video_id: UUID, payload: ContentPayload, actor_id: UUID
) -> dict:
    payload.contentType = "VIDEO"
    return await update_content(session, redis, video_id, payload, actor_id)


async def delete_admin_video(
    session: AsyncSession, redis: Redis, video_id: UUID, actor_id: UUID
) -> dict:
    updated_count = await admin_content_repo.soft_delete_admin_video_record(session, id=video_id, actor_id=actor_id)
    if updated_count == 0:
        raise HTTPException(status_code=404, detail="Video not found.")
    await admin_content_repo.audit_admin_event(session, actor_id=actor_id, event_type="video_deleted", resource="content", metadata={"videoId": str(video_id), "mode": "soft_delete"})
    await session.commit()
    await invalidate_content_storefront_cache(redis)
    return {"ok": True, "action": "archived"}


async def reply_admin_video_comment(
    session: AsyncSession,
    video_id: UUID,
    comment_id: UUID,
    payload: AdminVideoCommentReplyPayload,
    actor_id: UUID,
) -> dict:
    target = await content_comment_repo.get_video_comment_for_reply(session, comment_id=comment_id, video_id=video_id)
    if not target:
        raise HTTPException(status_code=404, detail="Comment not found.")
    root_parent_id = target["parent_id"] or comment_id
    try:
        root_parent_uuid = UUID(str(root_parent_id))
    except Exception:
        root_parent_uuid = root_parent_id
        
    actor = await public_content_repo.get_user_full_name(session, actor_id) or "Admin"
    reply_id = uuid4()
    await content_comment_repo.insert_admin_video_comment_reply(
        session,
        id=reply_id,
        video_id=video_id,
        actor_id=actor_id,
        user_name=actor,
        body=sanitize_review_text(payload.body).strip(),
        parent_id=root_parent_uuid,
        reply_to_user_name=target["user_name"],
    )
    await admin_content_repo.audit_admin_event(session, actor_id=actor_id, event_type="video_comment_replied", resource="content", metadata={"videoId": str(video_id), "commentId": str(comment_id), "replyId": str(reply_id)})
    await session.commit()
    return {"id": str(reply_id)}


async def update_admin_video_comment(
    session: AsyncSession,
    video_id: UUID,
    comment_id: UUID,
    payload: AdminVideoCommentVisibilityPayload,
    actor_id: UUID,
) -> dict:
    updated_count = await content_comment_repo.update_video_comment_visibility_in_db(
        session, comment_id=comment_id, video_id=video_id, is_hidden=payload.isHidden, actor_id=actor_id
    )
    if updated_count == 0:
        raise HTTPException(status_code=404, detail="Comment not found.")
    await admin_content_repo.audit_admin_event(session, actor_id=actor_id, event_type="video_comment_visibility_updated", resource="content", metadata={"videoId": str(video_id), "commentId": str(comment_id), "isHidden": payload.isHidden})
    await session.commit()
    return {"ok": True}


async def list_admin_image_comments(session: AsyncSession) -> list[dict]:
    return await content_comment_repo.list_admin_image_comments(session)


async def reply_admin_image_comment(
    session: AsyncSession,
    comment_id: UUID,
    payload: AdminVideoCommentReplyPayload,
    actor_id: UUID,
) -> dict:
    target = await content_comment_repo.get_image_comment_for_reply(session, comment_id)
    if not target:
        raise HTTPException(status_code=404, detail="Comment not found.")
    actor = await public_content_repo.get_user_full_name(session, actor_id) or "Admin"
    reply_id = uuid4()
    
    product_id = target["product_id"]
    try:
        product_uuid = UUID(str(product_id))
    except Exception:
        product_uuid = product_id
        
    parent_id = target["parent_id"] or comment_id
    try:
        parent_uuid = UUID(str(parent_id))
    except Exception:
        parent_uuid = parent_id
        
    await content_comment_repo.insert_admin_image_comment_reply(
        session,
        id=reply_id,
        product_id=product_uuid,
        image_url=target["image_url"],
        actor_id=actor_id,
        user_name=actor,
        body=sanitize_review_text(payload.body).strip(),
        parent_id=parent_uuid,
        reply_to_user_name=target["user_name"],
        interaction_type=target.get("interaction_type") or "IMAGE_COMMENT",
    )
    await admin_content_repo.audit_admin_event(session, actor_id=actor_id, event_type="image_comment_replied", resource="review", metadata={"commentId": str(comment_id), "replyId": str(reply_id)})
    await session.commit()
    return {"id": str(reply_id)}


async def update_admin_image_comment(
    session: AsyncSession,
    comment_id: UUID,
    payload: AdminVideoCommentVisibilityPayload,
    actor_id: UUID,
) -> dict:
    updated_count = await content_comment_repo.update_image_comment_visibility_in_db(
        session, comment_id=comment_id, is_hidden=payload.isHidden
    )
    if updated_count == 0:
        raise HTTPException(status_code=404, detail="Comment not found.")
    await admin_content_repo.audit_admin_event(session, actor_id=actor_id, event_type="image_comment_visibility_updated", resource="review", metadata={"commentId": str(comment_id), "isHidden": payload.isHidden})
    await session.commit()
    return {"ok": True}
