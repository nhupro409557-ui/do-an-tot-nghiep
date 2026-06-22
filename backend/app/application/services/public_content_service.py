import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.content import (
    ProductImageCommentRequest,
    ProductQuestionRequest,
    ReviewRequest,
    ReviewUpdateRequest,
    VideoCommentRequest,
    VideoViewHeartbeatRequest,
)
from app.infrastructure.database.repositories import (
    content_comment_repo,
    public_content_repo,
)
from app.infrastructure.cache import (
    safe_redis_expire,
    safe_redis_get,
    safe_redis_sadd,
    safe_redis_setex,
)
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



SENSITIVE_COMMENT_TERMS = {
    "chửi", "địt", "đụ", "cặc", "lồn", "đéo", "dm", "đm", "fuck", "shit", "scam", "lừa đảo"
}


def content_cache_key(page: int, limit: int) -> str:
    return f"storefront:content:videos:page:{page}:limit:{limit}"


def banner_cache_key(limit: int) -> str:
    return f"storefront:content:banners:limit:{limit}"


def youtube_embed_url(value: str | None) -> str | None:
    if not value:
        return None
    text_value = str(value).strip()
    if "youtube.com/embed/" in text_value:
        return text_value
    if "youtu.be/" in text_value:
        video_id = text_value.split("youtu.be/", 1)[1].split("?", 1)[0].split("/", 1)[0]
        return f"https://www.youtube.com/embed/{video_id}"
    if "youtube.com/shorts/" in text_value:
        video_id = text_value.split("youtube.com/shorts/", 1)[1].split("?", 1)[0].split("/", 1)[0]
        return f"https://www.youtube.com/embed/{video_id}"
    if "youtube.com/watch" in text_value and "v=" in text_value:
        video_id = text_value.split("v=", 1)[1].split("&", 1)[0]
        return f"https://www.youtube.com/embed/{video_id}"
    return None


def youtube_thumbnail_url(value: str | None) -> str | None:
    embed = youtube_embed_url(value)
    if not embed:
        return None
    video_id = embed.rstrip("/").split("/")[-1].split("?")[0]
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else None


def detect_sensitive_comment(value: str) -> str | None:
    lowered = value.lower()
    for term in SENSITIVE_COMMENT_TERMS:
        if term in lowered:
            return f"Tự động ẩn do chứa từ nhạy cảm: {term}"
    spam_reason = detect_spam_reason(value, [])
    return spam_reason


async def get_existing_review(*, product_id: UUID, user_id: UUID, session: AsyncSession) -> dict | None:
    return await public_content_repo.get_existing_review(session, product_id=product_id, user_id=user_id)


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
        message = "Bạn đã đánh giá sản phẩm này. Bạn có thể sửa hoặc xóa trong thời gian cho phép."
    elif order_outcome == "DA_HOAN_TIEN":
        message = "Đơn hàng liên quan đã hoàn tiền, đánh giá mới không còn khả dụng."
    elif order_outcome == "DA_TRA_HANG":
        message = "Đơn hàng liên quan đã trả hàng, đánh giá mới không còn khả dụng."
    elif has_completed_order and not within_window:
        message = f"Đã hết hạn đánh giá. Chỉ cho phép đánh giá trong vòng {REVIEW_WINDOW_DAYS} ngày sau khi hoàn thành đơn."
    elif has_completed_order:
        message = "Bạn có thể đánh giá sản phẩm này."
    else:
        message = "Chỉ khách hàng có đơn hàng đã hoàn thành mới có thể đánh giá sản phẩm này."

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


async def list_reviews(product_id: UUID, session: AsyncSession) -> list[dict]:
    return await public_content_repo.list_reviews(session, product_id)


async def review_eligibility(
    product_id: UUID,
    current_user_id: UUID,
    session: AsyncSession,
) -> dict:
    return await get_review_eligibility(product_id, current_user_id, session)


async def create_review(
    product_id: UUID,
    payload: ReviewRequest,
    current_user_id: UUID,
    session: AsyncSession,
) -> dict:
    eligibility = await get_review_eligibility(product_id, current_user_id, session)
    if not eligibility["canReview"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=eligibility["message"])

    await enforce_review_rate_limit(session=session, user_id=current_user_id)
    media_urls = sanitize_media_urls(payload.mediaUrls)
    safe_user_name = sanitize_review_text(payload.userName)[:255]
    safe_comment = sanitize_review_text(payload.comment)
    normalized_comment = normalize_review_text(safe_comment)

    duplicate_review = await public_content_repo.has_duplicate_review(
        session,
        user_id=current_user_id,
        product_id=product_id,
        normalized_comment=normalized_comment,
    )
    if duplicate_review:
        raise HTTPException(status_code=409, detail="Đánh giá trùng nội dung trước đó. Vui lòng chỉnh sửa nhận xét trước khi gửi lại.")

    # Suspicious reviews are kept in moderation so the shop can inspect them instead of losing traceability.
    spam_reason = detect_spam_reason(safe_comment, media_urls)
    moderation_note = "Tự động chờ duyệt trước khi public."
    if spam_reason:
        moderation_note = f"Tự động giữ lại để kiểm tra spam: {spam_reason}"

    latest_order = await get_latest_reviewable_order(session=session, user_id=current_user_id, product_id=product_id)
    _, expires_at = compute_review_window(latest_order)

    review_id = uuid4()
    await public_content_repo.insert_review(
        session,
        review_id=review_id,
        product_id=product_id,
        order_id=UUID(str(latest_order["id"])) if latest_order else None,
        user_id=current_user_id,
        user_name=safe_user_name,
        rating=payload.rating,
        comment=safe_comment,
        media_urls=dumps_json(media_urls),
        moderation_note=moderation_note,
        is_spam=bool(spam_reason),
        spam_reason=spam_reason,
        review_window_expires_at=expires_at,
    )
    await sync_product_review_stats(session=session, product_id=product_id)
    await session.commit()
    return {
        "id": str(review_id),
        "status": "PENDING",
        "message": "Đánh giá đã được gửi và đang chờ kiểm duyệt trước khi hiển thị công khai.",
    }


async def update_own_review(
    product_id: UUID,
    review_id: UUID,
    payload: ReviewUpdateRequest,
    current_user_id: UUID,
    session: AsyncSession,
) -> dict:
    review = await public_content_repo.get_own_review_for_edit(
        session,
        review_id=review_id,
        product_id=product_id,
        user_id=current_user_id,
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    expires_at = review["review_window_expires_at"]
    if not expires_at or datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=403, detail="Đã hết hạn chỉnh sửa đánh giá.")

    eligibility = await get_review_eligibility(product_id, current_user_id, session)
    if eligibility.get("orderOutcome") is not None:
        raise HTTPException(status_code=403, detail="Đánh giá này gắn với đơn hàng đã trả/hoàn, không thể chỉnh sửa.")

    media_urls = sanitize_media_urls(payload.mediaUrls)
    safe_user_name = sanitize_review_text(payload.userName)[:255]
    safe_comment = sanitize_review_text(payload.comment)
    normalized_comment = normalize_review_text(safe_comment)
    duplicate_review = await public_content_repo.has_duplicate_review(
        session,
        user_id=current_user_id,
        product_id=product_id,
        normalized_comment=normalized_comment,
        exclude_review_id=review_id,
    )
    if duplicate_review:
        raise HTTPException(status_code=409, detail="Nội dung đánh giá bị trùng với một đánh giá khác của bạn.")

    spam_reason = detect_spam_reason(safe_comment, media_urls)
    moderation_note = "Người dùng đã sửa đánh giá, cần duyệt lại."
    if spam_reason:
        moderation_note = f"Bản sửa đánh giá bị giữ lại để kiểm tra spam: {spam_reason}"

    await public_content_repo.update_review_for_moderation(
        session,
        review_id=review_id,
        user_name=safe_user_name,
        rating=payload.rating,
        comment=safe_comment,
        media_urls=dumps_json(media_urls),
        moderation_note=moderation_note,
        is_spam=bool(spam_reason),
        spam_reason=spam_reason,
    )
    await sync_product_review_stats(session=session, product_id=product_id)
    await session.commit()
    return {"ok": True, "status": "PENDING", "message": "Đánh giá đã được cập nhật và quay lại hàng đợi kiểm duyệt."}


async def delete_own_review(
    product_id: UUID,
    review_id: UUID,
    current_user_id: UUID,
    session: AsyncSession,
) -> dict:
    review = await public_content_repo.get_own_review_for_edit(
        session,
        review_id=review_id,
        product_id=product_id,
        user_id=current_user_id,
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")
    expires_at = review["review_window_expires_at"]
    if not expires_at or datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=403, detail="Đã hết hạn xóa đánh giá.")

    deleted_count = await public_content_repo.delete_review(session, review_id)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Review not found.")
    await sync_product_review_stats(session=session, product_id=product_id)
    await session.commit()
    return {"ok": True}


async def list_notifications(
    current_user_id: UUID,
    session: AsyncSession,
) -> list[dict]:
    return await public_content_repo.list_notifications(session, current_user_id)


async def mark_notifications_read(
    current_user_id: UUID,
    session: AsyncSession,
) -> dict[str, bool]:
    await public_content_repo.mark_notifications_read(session, current_user_id)
    await session.commit()
    return {"ok": True}


async def list_rewards(session: AsyncSession) -> list[dict]:
    return await public_content_repo.list_rewards(session)


async def list_banners(
    limit: int,
    session: AsyncSession,
    redis: Redis,
) -> list[dict]:
    cache_key = banner_cache_key(limit)
    cached = await safe_redis_get(redis, cache_key)
    if cached:
        return json.loads(cached)

    rows = await public_content_repo.list_banners(session, limit)
    items = []
    for item in rows:
        product = item.get("product") or {}
        category = item.get("category") or {}
        if product.get("id"):
            item["href"] = f"/product/{product.get('slug') or product.get('id')}"
        elif category.get("id") or category.get("slug"):
            item["href"] = f"/products/{category.get('slug') or category.get('id')}"
        else:
            item["href"] = "/products"
        items.append(item)
    if await safe_redis_setex(redis, cache_key, 300, json.dumps(items, ensure_ascii=False, default=str)):
        await safe_redis_sadd(redis, "storefront:content:banners:keys", cache_key)
        await safe_redis_expire(redis, "storefront:content:banners:keys", 24 * 60 * 60)
    return items


async def list_videos(
    page: int,
    limit: int,
    session: AsyncSession,
    redis: Redis,
) -> dict:
    cache_key = content_cache_key(page, limit)
    cached = await safe_redis_get(redis, cache_key)
    if cached:
        return json.loads(cached)

    offset = (page - 1) * limit
    items = await public_content_repo.list_videos(session, limit=limit, offset=offset)
    for item in items:
        item["embedUrl"] = youtube_embed_url(item.get("videoUrl")) if item.get("videoSource") == "YOUTUBE" else None
        item["youtubeThumbnailUrl"] = youtube_thumbnail_url(item.get("videoUrl")) if item.get("videoSource") == "YOUTUBE" else None
    total = await public_content_repo.count_published_videos(session)
    payload = {
        "items": items,
        "page": page,
        "limit": limit,
        "total": int(total),
        "hasMore": offset + len(items) < int(total),
    }
    if await safe_redis_setex(redis, cache_key, 300, json.dumps(payload, ensure_ascii=False, default=str)):
        await safe_redis_sadd(redis, "storefront:content:videos:keys", cache_key)
        await safe_redis_expire(redis, "storefront:content:videos:keys", 24 * 60 * 60)
    return payload


async def record_video_view(
    video_id: UUID,
    payload: VideoViewHeartbeatRequest,
    fingerprint: str,
    session: AsyncSession,
    redis: Redis,
) -> dict:
    exists = await public_content_repo.published_video_exists(session, video_id)
    if not exists:
        raise HTTPException(status_code=404, detail="Video not found.")
    if not payload.visible:
        return {"counted": False}

    base_key = f"video:view:{video_id}:{fingerprint}"
    counted_key = f"{base_key}:counted"
    try:
        if await redis.get(counted_key):
            return {"counted": False}
        watched = await redis.incrby(base_key, payload.watchedSeconds)
        await redis.expire(base_key, 60 * 60)
        if watched < 30:
            return {"counted": False, "watchedSeconds": int(watched)}
        await redis.setex(counted_key, 24 * 60 * 60, "1")
        await redis.delete(base_key)
    except Exception:
        pass

    view_count = await public_content_repo.increment_video_view_count(session, video_id)
    if view_count is None:
        raise HTTPException(status_code=404, detail="Video not found.")
    await session.commit()
    return {"counted": True, "viewCount": int(view_count)}


async def toggle_video_like(
    video_id: UUID,
    session: AsyncSession,
    current_user_id: UUID,
) -> dict:
    exists = await public_content_repo.video_exists(session, video_id)
    if not exists:
        raise HTTPException(status_code=404, detail="Video not found.")
    liked = await public_content_repo.user_liked_video(session, video_id=video_id, user_id=current_user_id)
    if liked:
        await public_content_repo.delete_video_like(session, video_id=video_id, user_id=current_user_id)
        is_liked = False
    else:
        await public_content_repo.insert_video_like(session, video_id=video_id, user_id=current_user_id)
        is_liked = True
    like_count = await public_content_repo.count_video_likes(session, video_id)
    await session.commit()
    return {"liked": is_liked, "likeCount": int(like_count)}


async def create_video_comment(
    video_id: UUID,
    payload: VideoCommentRequest,
    session: AsyncSession,
    current_user_id: UUID,
) -> dict:
    video_exists = await public_content_repo.published_video_exists(session, video_id)
    if not video_exists:
        raise HTTPException(status_code=404, detail="Video not found.")

    parent_id = payload.parentId
    reply_to_user_name = payload.replyToUserName
    if parent_id:
        parent = await content_comment_repo.get_video_comment_parent(session, parent_id=parent_id, video_id=video_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found.")
        if parent["parent_id"]:
            parent_id = parent["parent_id"]
        reply_to_user_name = reply_to_user_name or parent["user_name"]

    user_name = await public_content_repo.get_user_full_name(session, current_user_id) or "Khách hàng"
    clean_body = sanitize_review_text(payload.body).strip()
    moderation_reason = detect_sensitive_comment(clean_body)
    comment_id = uuid4()
    await content_comment_repo.insert_video_comment(
        session,
        comment_id=comment_id,
        video_id=video_id,
        user_id=current_user_id,
        user_name=user_name,
        body=clean_body,
        parent_id=parent_id,
        reply_to_user_name=reply_to_user_name,
        is_hidden=bool(moderation_reason),
        moderation_reason=moderation_reason,
    )
    await session.commit()
    return {
        "id": str(comment_id),
        "userName": user_name,
        "content": clean_body,
        "parentId": str(parent_id) if parent_id else None,
        "replyToUserName": reply_to_user_name,
        "isHidden": bool(moderation_reason),
        "moderationReason": moderation_reason,
    }


async def retract_video_comment(
    video_id: UUID,
    comment_id: UUID,
    session: AsyncSession,
    current_user_id: UUID,
) -> dict:
    updated_count = await content_comment_repo.retract_video_comment(session, video_id=video_id, comment_id=comment_id, user_id=current_user_id)
    if updated_count == 0:
        raise HTTPException(status_code=404, detail="Comment not found.")
    await session.commit()
    return {"ok": True}


async def list_product_image_comments(product_id: UUID, session: AsyncSession) -> list[dict]:
    return await content_comment_repo.list_product_image_comments(session, product_id, interaction_type="IMAGE_COMMENT")


async def create_product_image_comment(
    product_id: UUID,
    payload: ProductImageCommentRequest,
    session: AsyncSession,
    current_user_id: UUID,
) -> dict:
    exists = await public_content_repo.product_exists(session, product_id)
    if not exists:
        raise HTTPException(status_code=404, detail="Product not found.")
    parent_id = payload.parentId
    reply_to_user_name = payload.replyToUserName
    if parent_id:
        parent = await content_comment_repo.get_product_image_comment_parent(session, parent_id=parent_id, product_id=product_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found.")
        if parent["parent_id"]:
            parent_id = parent["parent_id"]
            reply_to_user_name = reply_to_user_name or parent["user_name"]
    user_name = await public_content_repo.get_user_full_name(session, current_user_id) or "Khách hàng"
    clean_body = sanitize_review_text(payload.body).strip()
    moderation_reason = detect_sensitive_comment(clean_body)
    comment_id = uuid4()
    await content_comment_repo.insert_product_image_comment(
        session,
        comment_id=comment_id,
        product_id=product_id,
        image_url=payload.imageUrl,
        user_id=current_user_id,
        user_name=user_name,
        body=clean_body,
        parent_id=parent_id,
        reply_to_user_name=reply_to_user_name,
        is_hidden=bool(moderation_reason),
        moderation_reason=moderation_reason,
        interaction_type="IMAGE_COMMENT",
    )
    await session.commit()
    return {
        "id": str(comment_id),
        "userName": user_name,
        "content": clean_body if not moderation_reason else "Bình luận đang chờ kiểm duyệt.",
        "parentId": str(parent_id) if parent_id else None,
        "replyToUserName": reply_to_user_name,
        "isHidden": bool(moderation_reason),
        "isRetracted": False,
    }


async def retract_product_image_comment(
    product_id: UUID,
    comment_id: UUID,
    session: AsyncSession,
    current_user_id: UUID,
) -> dict:
    updated_count = await content_comment_repo.retract_product_image_comment(session, product_id=product_id, comment_id=comment_id, user_id=current_user_id)
    if updated_count == 0:
        raise HTTPException(status_code=404, detail="Comment not found.")
    await session.commit()
    return {"ok": True}


async def list_product_questions(product_id: UUID, session: AsyncSession) -> list[dict]:
    return await content_comment_repo.list_product_image_comments(session, product_id, interaction_type="PRODUCT_QA")


async def create_product_question(
    product_id: UUID,
    payload: ProductQuestionRequest,
    session: AsyncSession,
    current_user_id: UUID,
) -> dict:
    exists = await public_content_repo.product_exists(session, product_id)
    if not exists:
        raise HTTPException(status_code=404, detail="Product not found.")
    parent_id = payload.parentId
    reply_to_user_name = payload.replyToUserName
    if parent_id:
        parent = await content_comment_repo.get_product_image_comment_parent(
            session,
            parent_id=parent_id,
            product_id=product_id,
            interaction_type="PRODUCT_QA",
        )
        if not parent:
            raise HTTPException(status_code=404, detail="Parent question not found.")
        if parent["parent_id"]:
            parent_id = parent["parent_id"]
            reply_to_user_name = reply_to_user_name or parent["user_name"]
    user_name = await public_content_repo.get_user_full_name(session, current_user_id) or "Khách hàng"
    clean_body = sanitize_review_text(payload.body).strip()
    moderation_reason = detect_sensitive_comment(clean_body)
    comment_id = uuid4()
    await content_comment_repo.insert_product_image_comment(
        session,
        comment_id=comment_id,
        product_id=product_id,
        image_url=None,
        user_id=current_user_id,
        user_name=user_name,
        body=clean_body,
        parent_id=parent_id,
        reply_to_user_name=reply_to_user_name,
        is_hidden=bool(moderation_reason),
        moderation_reason=moderation_reason,
        interaction_type="PRODUCT_QA",
    )
    await session.commit()
    return {
        "id": str(comment_id),
        "userName": user_name,
        "content": clean_body if not moderation_reason else "Câu hỏi đang chờ kiểm duyệt.",
        "parentId": str(parent_id) if parent_id else None,
        "replyToUserName": reply_to_user_name,
        "isHidden": bool(moderation_reason),
        "isRetracted": False,
    }


async def retract_product_question(
    product_id: UUID,
    comment_id: UUID,
    session: AsyncSession,
    current_user_id: UUID,
) -> dict:
    updated_count = await content_comment_repo.retract_product_image_comment(
        session,
        product_id=product_id,
        comment_id=comment_id,
        user_id=current_user_id,
        interaction_type="PRODUCT_QA",
    )
    if updated_count == 0:
        raise HTTPException(status_code=404, detail="Question not found.")
    await session.commit()
    return {"ok": True}
