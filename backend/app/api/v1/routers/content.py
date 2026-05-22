import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session
from app.shared.reviews import (
    REVIEW_WINDOW_DAYS,
    compute_review_window,
    detect_spam_reason,
    dumps_json,
    enforce_review_rate_limit,
    get_latest_reviewable_order,
    normalize_review_text,
    review_order_outcome_label,
    sanitize_media_urls,
    sanitize_review_text,
    sync_product_review_stats,
)


router = APIRouter(tags=["Content"])


def content_cache_key(page: int, limit: int) -> str:
    return f"storefront:content:videos:page:{page}:limit:{limit}"


class ReviewRequest(BaseModel):
    userName: str = Field(min_length=1, max_length=255)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1, max_length=2000)
    mediaUrls: list[str] = Field(default_factory=list, max_length=6)


class ReviewUpdateRequest(BaseModel):
    userName: str = Field(min_length=1, max_length=255)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1, max_length=2000)
    mediaUrls: list[str] = Field(default_factory=list, max_length=6)


async def get_existing_review(*, product_id: UUID, user_id: UUID, session: AsyncSession) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    id::text,
                    product_id::text AS "productId",
                    order_id::text AS "orderId",
                    user_name AS "userName",
                    rating,
                    comment,
                    media_urls AS "mediaUrls",
                    status,
                    moderation_note AS "moderationNote",
                    review_window_expires_at AS "reviewWindowExpiresAt",
                    edited_at AS "editedAt",
                    created_at AS "createdAt",
                    updated_at AS "updatedAt"
                FROM product_reviews
                WHERE user_id = :user_id
                  AND product_id = :product_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"user_id": user_id, "product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_review_eligibility(product_id: UUID, user_id: UUID, session: AsyncSession) -> dict:
    latest_order = await get_latest_reviewable_order(session=session, user_id=user_id, product_id=product_id)
    existing_review = await get_existing_review(product_id=product_id, user_id=user_id, session=session)
    has_completed_order = bool(latest_order)
    within_window, expires_at = compute_review_window(latest_order)
    already_reviewed = bool(existing_review)
    order_outcome = review_order_outcome_label(latest_order["status"]) if latest_order else None
    can_review = has_completed_order and within_window and not already_reviewed and order_outcome is None

    existing_expires_at = existing_review.get("reviewWindowExpiresAt") if existing_review else None
    if isinstance(existing_expires_at, str):
        existing_expires_at = datetime.fromisoformat(existing_expires_at)
    can_edit = bool(existing_review and existing_expires_at and datetime.now(timezone.utc) <= existing_expires_at and order_outcome is None)
    can_delete = can_edit

    if existing_review:
        message = "Ban da danh gia san pham nay. Ban co the sua hoac xoa trong thoi gian cho phep."
    elif order_outcome == "DA_HOAN_TIEN":
        message = "Don hang lien quan da hoan tien, danh gia moi khong con kha dung."
    elif order_outcome == "DA_TRA_HANG":
        message = "Don hang lien quan da tra hang, danh gia moi khong con kha dung."
    elif has_completed_order and not within_window:
        message = f"Da het han danh gia. Chi cho phep danh gia trong vong {REVIEW_WINDOW_DAYS} ngay sau khi hoan thanh don."
    elif has_completed_order:
        message = "Ban co the danh gia san pham nay."
    else:
        message = "Chi khach hang co don hang da hoan thanh moi co the danh gia san pham nay."

    return {
        "canReview": can_review,
        "hasCompletedOrder": has_completed_order,
        "alreadyReviewed": already_reviewed,
        "withinReviewWindow": within_window,
        "reviewWindowExpiresAt": expires_at,
        "canEdit": can_edit,
        "canDelete": can_delete,
        "orderOutcome": order_outcome,
        "existingReview": existing_review,
        "message": message,
    }


@router.get("/products/{product_id}/reviews")
async def list_reviews(product_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                pr.id::text,
                pr.product_id::text AS "productId",
                pr.user_id::text AS "userId",
                pr.user_name AS "userName",
                pr.rating,
                pr.comment,
                pr.media_urls AS "mediaUrls",
                pr.shop_reply AS "shopReply",
                pr.shop_replied_at AS "shopRepliedAt",
                CASE
                    WHEN o.status = 'REFUNDED' THEN 'DA_HOAN_TIEN'
                    WHEN o.status = 'RETURNED' THEN 'DA_TRA_HANG'
                    ELSE NULL
                END AS "orderOutcome",
                pr.created_at AS "createdAt"
            FROM product_reviews pr
            LEFT JOIN orders o ON o.id = pr.order_id
            WHERE pr.product_id = :product_id AND pr.status = 'PUBLISHED'
            ORDER BY pr.created_at DESC
            """
        ),
        {"product_id": product_id},
    )
    return [dict(row._mapping) for row in result]


@router.get("/products/{product_id}/reviews/eligibility")
async def review_eligibility(
    product_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await get_review_eligibility(product_id, current_user_id, session)


@router.post("/products/{product_id}/reviews", status_code=status.HTTP_201_CREATED)
async def create_review(
    product_id: UUID,
    payload: ReviewRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    eligibility = await get_review_eligibility(product_id, current_user_id, session)
    if not eligibility["canReview"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=eligibility["message"])

    await enforce_review_rate_limit(session=session, user_id=current_user_id)
    media_urls = sanitize_media_urls(payload.mediaUrls)
    safe_user_name = sanitize_review_text(payload.userName)[:255]
    safe_comment = sanitize_review_text(payload.comment)
    normalized_comment = normalize_review_text(safe_comment)

    duplicate_review = await session.scalar(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM product_reviews
                WHERE user_id = :user_id
                  AND product_id = :product_id
                  AND lower(trim(comment)) = :normalized_comment
            )
            """
        ),
        {
            "user_id": current_user_id,
            "product_id": product_id,
            "normalized_comment": normalized_comment,
        },
    )
    if duplicate_review:
        raise HTTPException(status_code=409, detail="Danh gia trung noi dung truoc do. Vui long chinh sua nhan xet truoc khi gui lai.")

    # Suspicious reviews are kept in moderation so the shop can inspect them instead of losing traceability.
    spam_reason = detect_spam_reason(safe_comment, media_urls)
    moderation_note = "Tu dong cho duyet truoc khi public."
    if spam_reason:
        moderation_note = f"Tu dong giu lai de kiem tra spam: {spam_reason}"

    latest_order = await get_latest_reviewable_order(session=session, user_id=current_user_id, product_id=product_id)
    _, expires_at = compute_review_window(latest_order)

    review_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO product_reviews (
                id, product_id, order_id, user_id, user_name, rating, comment, media_urls,
                status, moderation_note, is_spam, spam_reason, review_window_expires_at
            )
            VALUES (
                :id, :product_id, :order_id, :user_id, :user_name, :rating, :comment, CAST(:media_urls AS jsonb),
                'PENDING', :moderation_note, :is_spam, :spam_reason, :review_window_expires_at
            )
            """
        ),
        {
            "id": review_id,
            "product_id": product_id,
            "order_id": UUID(str(latest_order["id"])) if latest_order else None,
            "user_id": current_user_id,
            "user_name": safe_user_name,
            "rating": payload.rating,
            "comment": safe_comment,
            "media_urls": dumps_json(media_urls),
            "moderation_note": moderation_note,
            "is_spam": bool(spam_reason),
            "spam_reason": spam_reason,
            "review_window_expires_at": expires_at,
        },
    )
    await sync_product_review_stats(session=session, product_id=product_id)
    await session.commit()
    return {
        "id": str(review_id),
        "status": "PENDING",
        "message": "Danh gia da duoc gui va dang cho kiem duyet truoc khi hien thi cong khai.",
    }


@router.patch("/products/{product_id}/reviews/{review_id}")
async def update_own_review(
    product_id: UUID,
    review_id: UUID,
    payload: ReviewUpdateRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    review = (
        await session.execute(
            text(
                """
                SELECT id, review_window_expires_at
                FROM product_reviews
                WHERE id = :review_id
                  AND product_id = :product_id
                  AND user_id = :user_id
                """
            ),
            {"review_id": review_id, "product_id": product_id, "user_id": current_user_id},
        )
    ).mappings().first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    expires_at = review["review_window_expires_at"]
    if not expires_at or datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=403, detail="Da het han chinh sua danh gia.")

    eligibility = await get_review_eligibility(product_id, current_user_id, session)
    if eligibility.get("orderOutcome") is not None:
        raise HTTPException(status_code=403, detail="Danh gia nay gan voi don hang da tra/hoan, khong the chinh sua.")

    media_urls = sanitize_media_urls(payload.mediaUrls)
    safe_user_name = sanitize_review_text(payload.userName)[:255]
    safe_comment = sanitize_review_text(payload.comment)
    normalized_comment = normalize_review_text(safe_comment)
    duplicate_review = await session.scalar(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM product_reviews
                WHERE user_id = :user_id
                  AND product_id = :product_id
                  AND id <> :review_id
                  AND lower(trim(comment)) = :normalized_comment
            )
            """
        ),
        {
            "user_id": current_user_id,
            "product_id": product_id,
            "review_id": review_id,
            "normalized_comment": normalized_comment,
        },
    )
    if duplicate_review:
        raise HTTPException(status_code=409, detail="Noi dung danh gia bi trung voi mot danh gia khac cua ban.")

    spam_reason = detect_spam_reason(safe_comment, media_urls)
    moderation_note = "Nguoi dung da sua danh gia, can duyet lai."
    if spam_reason:
        moderation_note = f"Ban sua danh gia bi giu lai de kiem tra spam: {spam_reason}"

    await session.execute(
        text(
            """
            UPDATE product_reviews
            SET
                user_name = :user_name,
                rating = :rating,
                comment = :comment,
                media_urls = CAST(:media_urls AS jsonb),
                status = 'PENDING',
                moderation_note = :moderation_note,
                is_spam = :is_spam,
                spam_reason = :spam_reason,
                edited_at = NOW(),
                updated_at = NOW()
            WHERE id = :review_id
            """
        ),
        {
            "review_id": review_id,
            "user_name": safe_user_name,
            "rating": payload.rating,
            "comment": safe_comment,
            "media_urls": dumps_json(media_urls),
            "moderation_note": moderation_note,
            "is_spam": bool(spam_reason),
            "spam_reason": spam_reason,
        },
    )
    await sync_product_review_stats(session=session, product_id=product_id)
    await session.commit()
    return {"ok": True, "status": "PENDING", "message": "Danh gia da duoc cap nhat va quay lai hang doi kiem duyet."}


@router.delete("/products/{product_id}/reviews/{review_id}")
async def delete_own_review(
    product_id: UUID,
    review_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    review = (
        await session.execute(
            text(
                """
                SELECT id, review_window_expires_at
                FROM product_reviews
                WHERE id = :review_id
                  AND product_id = :product_id
                  AND user_id = :user_id
                """
            ),
            {"review_id": review_id, "product_id": product_id, "user_id": current_user_id},
        )
    ).mappings().first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    expires_at = review["review_window_expires_at"]
    if not expires_at or datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=403, detail="Da het han xoa danh gia.")

    result = await session.execute(text("DELETE FROM product_reviews WHERE id = :review_id"), {"review_id": review_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Review not found.")
    await sync_product_review_stats(session=session, product_id=product_id)
    await session.commit()
    return {"ok": True}


@router.get("/notifications")
async def list_notifications(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, type, title, message, read, created_at AS "createdAt"
            FROM notifications
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            """
        ),
        {"user_id": current_user_id},
    )
    return [dict(row._mapping) for row in result]


@router.patch("/notifications/read-all")
async def mark_notifications_read(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    await session.execute(
        text("UPDATE notifications SET read = TRUE WHERE user_id = :user_id"),
        {"user_id": current_user_id},
    )
    await session.commit()
    return {"ok": True}


@router.get("/rewards")
async def list_rewards(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, title, description, cost, image_url AS "imageUrl", is_active AS "isActive"
            FROM rewards
            WHERE is_active = TRUE
            ORDER BY cost, created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.get("/videos")
async def list_videos(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=48),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    cache_key = content_cache_key(page, limit)
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    offset = (page - 1) * limit
    result = await session.execute(
        text(
            """
            SELECT
                v.id::text,
                v.title,
                v.description,
                v.content_type AS "contentType",
                v.status,
                v.video_url AS "videoUrl",
                v.thumbnail_url AS "thumbnailUrl",
                v.banner_image_url AS "bannerImageUrl",
                v.like_count AS "likeCount",
                v.view_count AS "viewCount",
                v.sort_order AS "sortOrder",
                v.published_at AS "publishedAt",
                v.is_active AS "isActive",
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
                                'isHidden', cc.is_hidden,
                                'createdAt', cc.created_at
                            )
                            ORDER BY cc.created_at ASC
                        )
                        FROM content_comments cc
                        WHERE cc.content_id = v.id
                          AND cc.deleted_at IS NULL
                          AND cc.is_hidden = FALSE
                    ),
                    '[]'::json
                ) AS comments
            FROM videos v
            WHERE v.is_active = TRUE
              AND v.deleted_at IS NULL
              AND v.content_type = 'VIDEO'
              AND v.status = 'PUBLISHED'
              AND (v.scheduled_at IS NULL OR v.scheduled_at <= NOW())
            ORDER BY v.sort_order DESC, COALESCE(v.published_at, v.created_at) DESC, v.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": limit, "offset": offset},
    )
    items = [dict(row._mapping) for row in result]
    total = await session.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM videos
            WHERE is_active = TRUE
              AND deleted_at IS NULL
              AND content_type = 'VIDEO'
              AND (scheduled_at IS NULL OR scheduled_at <= NOW())
            """
        )
    ) or 0
    payload = {
        "items": items,
        "page": page,
        "limit": limit,
        "total": int(total),
        "hasMore": offset + len(items) < int(total),
    }
    await redis.setex(cache_key, 300, json.dumps(payload, ensure_ascii=False, default=str))
    await redis.sadd("storefront:content:videos:keys", cache_key)
    await redis.expire("storefront:content:videos:keys", 24 * 60 * 60)
    return payload
