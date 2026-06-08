from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import ReviewStatusPayload
from app.infrastructure.database.repositories import review_repo
from app.shared.reviews import sanitize_review_text, sync_product_review_stats


async def list_admin_reviews(session: AsyncSession) -> list[dict]:
    return await review_repo.list_admin_reviews(session)


async def list_admin_review_summary(session: AsyncSession) -> list[dict]:
    return await review_repo.list_admin_review_summary(session)


def build_review_update(payload: ReviewStatusPayload) -> tuple[list[str], dict[str, object]]:
    updates: list[str] = []
    params: dict[str, object] = {}

    if payload.status is not None:
        updates.append("status = :status")
        params["status"] = payload.status
    if payload.moderationNote is not None:
        updates.append("moderation_note = :moderation_note")
        params["moderation_note"] = sanitize_review_text(payload.moderationNote).strip() or None
    if payload.shopReply is not None:
        updates.append("shop_reply = :shop_reply")
        updates.append("shop_replied_at = CASE WHEN :shop_reply IS NULL THEN NULL ELSE NOW() END")
        params["shop_reply"] = sanitize_review_text(payload.shopReply).strip() or None
    if payload.flaggedReason is not None:
        updates.append("flagged_reason = :flagged_reason")
        updates.append("flagged_at = CASE WHEN :flagged_reason IS NULL THEN NULL ELSE NOW() END")
        params["flagged_reason"] = sanitize_review_text(payload.flaggedReason).strip() or None
    if payload.isSpam is not None:
        updates.append("is_spam = :is_spam")
        params["is_spam"] = payload.isSpam
    if payload.spamReason is not None:
        updates.append("spam_reason = :spam_reason")
        params["spam_reason"] = sanitize_review_text(payload.spamReason).strip() or None

    if not updates:
        raise HTTPException(status_code=400, detail="No review fields supplied for update.")

    updates.append("updated_at = NOW()")
    return updates, params


def build_review_notification(next_status: str, product_name: str) -> tuple[str, str]:
    notification_copy = {
        "PUBLISHED": (
            "Đánh giá đã được duyệt",
            f"Đánh giá của bạn cho sản phẩm {product_name} đã được hiển thị công khai.",
        ),
        "REJECTED": (
            "Đánh giá chưa được duyệt",
            f"Đánh giá của bạn cho sản phẩm {product_name} chưa được duyệt. Vui lòng kiểm tra nội dung và gửi lại nếu cần.",
        ),
    }
    return notification_copy[next_status]


async def update_review_status(
    session: AsyncSession, review_id: UUID, payload: ReviewStatusPayload
) -> dict:
    review_row = await review_repo.get_review_for_admin_update(session, review_id)
    if not review_row:
        raise HTTPException(status_code=404, detail="Review not found.")

    updates, params = build_review_update(payload)
    updated_count = await review_repo.update_review_fields(session, review_id, updates, params)
    if updated_count == 0:
        raise HTTPException(status_code=404, detail="Review not found.")

    next_status = payload.status
    if (
        next_status in {"PUBLISHED", "REJECTED"}
        and next_status != review_row["status"]
        and review_row["user_id"] is not None
    ):
        title, message = build_review_notification(next_status, review_row["product_name"])
        await review_repo.insert_review_notification(
            session,
            user_id=review_row["user_id"],
            title=title,
            message=message,
        )

    await sync_product_review_stats(session=session, product_id=review_row["product_id"])
    await session.commit()
    return {"ok": True}


async def delete_review(session: AsyncSession, review_id: UUID) -> dict:
    product_id = await review_repo.get_review_product_id(session, review_id)
    if not product_id:
        raise HTTPException(status_code=404, detail="Review not found.")

    deleted_count = await review_repo.delete_review(session, review_id)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Review not found.")

    await sync_product_review_stats(session=session, product_id=product_id)
    await session.commit()
    return {"ok": True}
