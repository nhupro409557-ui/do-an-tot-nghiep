import json
import re
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id, require_permission
from app.api.v1.routers.admin_schemas import *
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session
from app.shared.reviews import sync_product_review_stats


router = APIRouter()

def normalize_content_type(value: str | None) -> str:
    candidate = (value or "VIDEO").strip().upper()
    return candidate if candidate in {"VIDEO", "BANNER", "MARKETING_PAGE"} else "VIDEO"


def normalize_content_status(value: str | None, *, scheduled_at: datetime | None, published_at: datetime | None, is_active: bool) -> str:
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
    await session.execute(text("DELETE FROM content_product_relations WHERE content_id = :content_id"), {"content_id": content_id})
    for product_id in product_ids:
        await session.execute(
            text(
                """
                INSERT INTO content_product_relations (content_id, product_id)
                VALUES (:content_id, :product_id)
                ON CONFLICT (content_id, product_id) DO NOTHING
                """
            ),
            {"content_id": content_id, "product_id": product_id},
        )


async def replace_content_category_relations(session: AsyncSession, content_id: UUID, category_ids: list[str]) -> None:
    await session.execute(text("DELETE FROM content_category_relations WHERE content_id = :content_id"), {"content_id": content_id})
    for category_id in category_ids:
        await session.execute(
            text(
                """
                INSERT INTO content_category_relations (content_id, category_id)
                VALUES (:content_id, :category_id)
                ON CONFLICT (content_id, category_id) DO NOTHING
                """
            ),
            {"content_id": content_id, "category_id": category_id},
        )


async def replace_content_comments(session: AsyncSession, content_id: UUID, comments: list[dict], actor_id: UUID) -> None:
    await session.execute(text("DELETE FROM content_comments WHERE content_id = :content_id"), {"content_id": content_id})
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
        await session.execute(
            text(
                """
                INSERT INTO content_comments (
                    id, content_id, user_name, body, parent_id, is_hidden, created_by, updated_by
                )
                VALUES (
                    :id, :content_id, :user_name, :body, :parent_id, :is_hidden, :created_by, :updated_by
                )
                """
            ),
            {
                "id": persisted_id,
                "content_id": content_id,
                "user_name": item["userName"],
                "body": item["content"],
                "parent_id": parent_uuid,
                "is_hidden": item["isHidden"],
                "created_by": actor_id,
                "updated_by": actor_id,
            },
        )


@router.get("/content", dependencies=[Depends(require_permission("content:read"))])
async def list_admin_content(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                v.id::text,
                v.title,
                v.description,
                v.content_type AS "contentType",
                v.video_source AS "videoSource",
                v.video_category AS "videoCategory",
                v.status,
                v.video_url AS "videoUrl",
                v.thumbnail_url AS "thumbnailUrl",
                v.banner_image_url AS "bannerImageUrl",
                v.content_body AS "contentBody",
                LEFT(COALESCE(v.content_body, ''), 320) AS "contentBodyPreview",
                v.cta_label AS "ctaLabel",
                v.cta_url AS "ctaUrl",
                COALESCE((SELECT COUNT(*) FROM video_likes vl WHERE vl.video_id = v.id), 0)::int AS "likeCount",
                v.view_count AS "viewCount",
                v.sort_order AS "sortOrder",
                v.scheduled_at AS "scheduledAt",
                v.published_at AS "publishedAt",
                v.is_active AS "isActive",
                v.created_by::text AS "createdBy",
                v.updated_by::text AS "updatedBy",
                v.deleted_at AS "deletedAt",
                v.version,
                v.created_at AS "createdAt",
                v.updated_at AS "updatedAt",
                COALESCE(
                    (
                        SELECT json_agg(json_build_object('id', p.id::text, 'name', p.name, 'brand', b.name, 'categoryId', p.category_id::text, 'imageUrl', p.image_url, 'price', p.sale_price))
                        FROM content_product_relations cpr
                        JOIN products p ON p.id = cpr.product_id
                        LEFT JOIN brands b ON b.id = p.brand_id
                        WHERE cpr.content_id = v.id
                    ),
                    '[]'::json
                ) AS products,
                COALESCE(
                    (
                        SELECT json_agg(cpr.product_id::text)
                        FROM content_product_relations cpr
                        WHERE cpr.content_id = v.id
                    ),
                    '[]'::json
                ) AS "productIds",
                COALESCE(
                    (
                        SELECT json_agg(json_build_object('id', c.id::text, 'name', c.name))
                        FROM content_category_relations ccr
                        JOIN categories c ON c.id = ccr.category_id
                        WHERE ccr.content_id = v.id
                    ),
                    '[]'::json
                ) AS categories,
                COALESCE(
                    (
                        SELECT json_agg(ccr.category_id::text)
                        FROM content_category_relations ccr
                        WHERE ccr.content_id = v.id
                    ),
                    '[]'::json
                ) AS "categoryIds",
                COALESCE(
                    (
                        SELECT json_agg(
                            json_build_object(
                                'id', cc.id::text,
                                'userName', cc.user_name,
                                'content', cc.body,
                                'parentId', cc.parent_id::text,
                                'replyToUserName', cc.reply_to_user_name,
                                'isHidden', cc.is_hidden,
                                'moderationReason', cc.moderation_reason,
                                'createdAt', cc.created_at
                            )
                            ORDER BY cc.created_at ASC
                        )
                        FROM content_comments cc
                        WHERE cc.content_id = v.id
                          AND cc.deleted_at IS NULL
                    ),
                    '[]'::json
                ) AS comments,
                (
                    SELECT COUNT(*)
                    FROM content_comments cc
                    WHERE cc.content_id = v.id
                      AND cc.deleted_at IS NULL
                ) AS "commentCount"
            FROM videos v
            WHERE v.deleted_at IS NULL
            ORDER BY v.sort_order DESC, COALESCE(v.scheduled_at, v.created_at) DESC, v.created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.post("/content", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("content:create"))])
async def create_content(
    payload: ContentPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    data = validate_content_payload(payload)
    content_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO videos (
                id, title, description, content_type, video_source, video_category, status, video_url, thumbnail_url, banner_image_url,
                content_body, cta_label, cta_url,
                like_count, view_count, sort_order, scheduled_at, published_at,
                is_active, version, created_by, updated_by, created_at, updated_at
            )
            VALUES (
                :id, :title, :description, :content_type, :video_source, :video_category, :status, :video_url, :thumbnail_url, :banner_image_url,
                :content_body, :cta_label, :cta_url,
                0, 0, :sort_order, :scheduled_at, :published_at,
                :is_active, 1, :created_by, :updated_by, NOW(), NOW()
            )
            """
        ),
        {"id": content_id, **data, "created_by": actor_id, "updated_by": actor_id},
    )
    await replace_content_product_relations(session, content_id, data["product_ids"])
    await replace_content_category_relations(session, content_id, data["category_ids"])
    await replace_content_comments(session, content_id, data["comments"], actor_id)
    await audit_admin_event(session, actor_id=actor_id, event_type="content_created", resource="content", metadata={"contentId": str(content_id), "contentType": data["content_type"], "videoCategory": data["video_category"], "status": data["status"]})
    await session.commit()
    await invalidate_content_storefront_cache(redis)
    return {"id": str(content_id)}


@router.patch("/content/{content_id}", dependencies=[Depends(require_permission("content:update"))])
async def update_content(
    content_id: UUID,
    payload: ContentPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    data = validate_content_payload(payload)
    expected_version = data.get("version")
    if expected_version is None:
        raise HTTPException(status_code=409, detail="Missing content version. Reload before saving.")
    result = await session.execute(
        text(
            """
            UPDATE videos
            SET
                title = :title,
                description = :description,
                content_type = :content_type,
                video_source = :video_source,
                video_category = :video_category,
                status = :status,
                video_url = :video_url,
                thumbnail_url = :thumbnail_url,
                banner_image_url = :banner_image_url,
                content_body = :content_body,
                cta_label = :cta_label,
                cta_url = :cta_url,
                sort_order = :sort_order,
                scheduled_at = :scheduled_at,
                published_at = :published_at,
                is_active = :is_active,
                version = version + 1,
                updated_by = :updated_by,
                updated_at = NOW()
            WHERE id = :id
              AND deleted_at IS NULL
              AND version = :expected_version
            """
        ),
        {"id": content_id, **data, "updated_by": actor_id, "expected_version": expected_version},
    )
    if result.rowcount == 0:
        exists = await session.scalar(text("SELECT COUNT(*) FROM videos WHERE id = :id AND deleted_at IS NULL"), {"id": content_id})
        if exists:
            raise HTTPException(status_code=409, detail="Content was updated by another admin. Reload before saving.")
        raise HTTPException(status_code=404, detail="Content not found.")
    await replace_content_product_relations(session, content_id, data["product_ids"])
    await replace_content_category_relations(session, content_id, data["category_ids"])
    await replace_content_comments(session, content_id, data["comments"], actor_id)
    await audit_admin_event(session, actor_id=actor_id, event_type="content_updated", resource="content", metadata={"contentId": str(content_id), "contentType": data["content_type"], "videoCategory": data["video_category"], "status": data["status"]})
    await session.commit()
    await invalidate_content_storefront_cache(redis)
    return {"ok": True}


@router.delete("/content/{content_id}", dependencies=[Depends(require_permission("content:delete"))])
async def delete_content(
    content_id: UUID,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    async with session.begin():
        result = await session.execute(
            text(
                """
                UPDATE videos
                SET deleted_at = NOW(), is_active = FALSE, status = 'ARCHIVED', version = version + 1, updated_by = :actor_id, updated_at = NOW()
                WHERE id = :id
                  AND deleted_at IS NULL
                """
            ),
            {"id": content_id, "actor_id": actor_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Content not found.")
        await audit_admin_event(session, actor_id=actor_id, event_type="content_deleted", resource="content", metadata={"contentId": str(content_id), "mode": "soft_delete"})
    await invalidate_content_storefront_cache(redis)
    return {"ok": True}


@router.get("/videos", dependencies=[Depends(require_permission("content:read"))])
async def list_admin_videos(session: AsyncSession = Depends(get_session)) -> list[dict]:
    items = await list_admin_content(session)
    return [item for item in items if item.get("contentType") == "VIDEO"]


@router.post("/videos", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("content:create"))])
async def create_admin_video(
    payload: ContentPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    payload.contentType = "VIDEO"
    return await create_content(payload, session, redis, actor_id)


@router.patch("/videos/{video_id}", dependencies=[Depends(require_permission("content:update"))])
async def update_admin_video(
    video_id: UUID,
    payload: ContentPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    payload.contentType = "VIDEO"
    return await update_content(video_id, payload, session, redis, actor_id)


@router.delete("/videos/{video_id}", dependencies=[Depends(require_permission("content:delete"))])
async def delete_admin_video(
    video_id: UUID,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    result = await session.execute(
        text("DELETE FROM videos WHERE id = :id AND content_type = 'VIDEO'"),
        {"id": video_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Video not found.")
    await audit_admin_event(session, actor_id=actor_id, event_type="video_deleted", resource="content", metadata={"videoId": str(video_id), "mode": "hard_delete"})
    await session.commit()
    await invalidate_content_storefront_cache(redis)
    return {"ok": True, "action": "deleted"}


@router.post("/videos/{video_id}/comments/{comment_id}/reply", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("content:update"))])
async def reply_admin_video_comment(
    video_id: UUID,
    comment_id: UUID,
    payload: AdminVideoCommentReplyPayload,
    session: AsyncSession = Depends(get_session),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    target = (
        await session.execute(
            text(
                """
                SELECT cc.id, cc.parent_id, cc.user_name, v.id AS video_id
                FROM content_comments cc
                JOIN videos v ON v.id = cc.content_id
                WHERE cc.id = :comment_id
                  AND cc.content_id = :video_id
                  AND v.content_type = 'VIDEO'
                  AND cc.deleted_at IS NULL
                """
            ),
            {"comment_id": comment_id, "video_id": video_id},
        )
    ).mappings().first()
    if not target:
        raise HTTPException(status_code=404, detail="Comment not found.")
    root_parent_id = target["parent_id"] or comment_id
    actor = (
        await session.execute(text("SELECT full_name FROM users WHERE id = :id"), {"id": actor_id})
    ).scalar_one_or_none() or "Admin"
    reply_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO content_comments (
                id, content_id, user_id, user_name, body, parent_id, reply_to_user_name,
                is_hidden, created_by, updated_by, created_at, updated_at
            )
            VALUES (
                :id, :video_id, :actor_id, :user_name, :body, :parent_id, :reply_to_user_name,
                FALSE, :actor_id, :actor_id, NOW(), NOW()
            )
            """
        ),
        {
            "id": reply_id,
            "video_id": video_id,
            "actor_id": actor_id,
            "user_name": actor,
            "body": sanitize_review_text(payload.body).strip(),
            "parent_id": root_parent_id,
            "reply_to_user_name": target["user_name"],
        },
    )
    await audit_admin_event(session, actor_id=actor_id, event_type="video_comment_replied", resource="content", metadata={"videoId": str(video_id), "commentId": str(comment_id), "replyId": str(reply_id)})
    await session.commit()
    return {"id": str(reply_id)}


@router.patch("/videos/{video_id}/comments/{comment_id}", dependencies=[Depends(require_permission("content:update"))])
async def update_admin_video_comment(
    video_id: UUID,
    comment_id: UUID,
    payload: AdminVideoCommentVisibilityPayload,
    session: AsyncSession = Depends(get_session),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    async with session.begin():
        result = await session.execute(
            text(
                """
                UPDATE content_comments
                SET is_hidden = :is_hidden, updated_by = :actor_id, updated_at = NOW()
                WHERE id = :comment_id
                  AND content_id = :video_id
                  AND deleted_at IS NULL
                """
            ),
            {"comment_id": comment_id, "video_id": video_id, "is_hidden": payload.isHidden, "actor_id": actor_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Comment not found.")
        await audit_admin_event(session, actor_id=actor_id, event_type="video_comment_visibility_updated", resource="content", metadata={"videoId": str(video_id), "commentId": str(comment_id), "isHidden": payload.isHidden})
    return {"ok": True}


@router.get("/image-comments", dependencies=[Depends(require_permission("review:read"))])
async def list_admin_image_comments(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                pic.id::text,
                pic.product_id::text AS "productId",
                p.name AS "productName",
                pic.image_url AS "imageUrl",
                pic.user_name AS "userName",
                CASE WHEN pic.is_retracted THEN 'Bình luận này đã bị thu hồi' ELSE pic.body END AS content,
                pic.parent_id::text AS "parentId",
                pic.reply_to_user_name AS "replyToUserName",
                pic.is_hidden AS "isHidden",
                pic.is_retracted AS "isRetracted",
                pic.moderation_reason AS "moderationReason",
                pic.created_at AS "createdAt"
            FROM product_image_comments pic
            JOIN products p ON p.id = pic.product_id
            ORDER BY pic.created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.post("/image-comments/{comment_id}/reply", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("review:update"))])
async def reply_admin_image_comment(
    comment_id: UUID,
    payload: AdminVideoCommentReplyPayload,
    session: AsyncSession = Depends(get_session),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    target = (
        await session.execute(
            text(
                """
                SELECT id, product_id, image_url, parent_id, user_name
                FROM product_image_comments
                WHERE id = :comment_id
                """
            ),
            {"comment_id": comment_id},
        )
    ).mappings().first()
    if not target:
        raise HTTPException(status_code=404, detail="Comment not found.")
    actor = (
        await session.execute(text("SELECT full_name FROM users WHERE id = :id"), {"id": actor_id})
    ).scalar_one_or_none() or "Admin"
    reply_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO product_image_comments (
                id, product_id, image_url, user_id, user_name, body, parent_id, reply_to_user_name,
                is_hidden, is_retracted, created_at, updated_at
            )
            VALUES (
                :id, :product_id, :image_url, :actor_id, :user_name, :body, :parent_id, :reply_to_user_name,
                FALSE, FALSE, NOW(), NOW()
            )
            """
        ),
        {
            "id": reply_id,
            "product_id": target["product_id"],
            "image_url": target["image_url"],
            "actor_id": actor_id,
            "user_name": actor,
            "body": sanitize_review_text(payload.body).strip(),
            "parent_id": target["parent_id"] or comment_id,
            "reply_to_user_name": target["user_name"],
        },
    )
    await audit_admin_event(session, actor_id=actor_id, event_type="image_comment_replied", resource="review", metadata={"commentId": str(comment_id), "replyId": str(reply_id)})
    await session.commit()
    return {"id": str(reply_id)}


@router.patch("/image-comments/{comment_id}", dependencies=[Depends(require_permission("review:update"))])
async def update_admin_image_comment(
    comment_id: UUID,
    payload: AdminVideoCommentVisibilityPayload,
    session: AsyncSession = Depends(get_session),
    actor_id: UUID = Depends(get_current_user_id),
) -> dict:
    result = await session.execute(
        text(
            """
            UPDATE product_image_comments
            SET is_hidden = :is_hidden, updated_at = NOW()
            WHERE id = :comment_id
            """
        ),
        {"comment_id": comment_id, "is_hidden": payload.isHidden},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Comment not found.")
    await audit_admin_event(session, actor_id=actor_id, event_type="image_comment_visibility_updated", resource="review", metadata={"commentId": str(comment_id), "isHidden": payload.isHidden})
    await session.commit()
    return {"ok": True}
