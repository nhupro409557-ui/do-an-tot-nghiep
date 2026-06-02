from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_permission
from app.api.v1.routers.admin_schemas import ReviewStatusPayload
from app.infrastructure.database.session import get_session
from app.shared.reviews import sanitize_review_text, sync_product_review_stats


router = APIRouter()

@router.get("/reviews", dependencies=[Depends(require_permission("review:read"))])
async def list_admin_reviews(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                pr.id::text,
                pr.product_id::text AS "productId",
                p.name AS "productName",
                pr.user_id::text AS "userId",
                pr.user_name AS "userName",
                pr.rating,
                pr.comment,
                pr.media_urls AS "mediaUrls",
                pr.status,
                pr.moderation_note AS "moderationNote",
                pr.shop_reply AS "shopReply",
                pr.shop_replied_at AS "shopRepliedAt",
                pr.flagged_reason AS "flaggedReason",
                pr.flagged_at AS "flaggedAt",
                pr.is_spam AS "isSpam",
                pr.spam_reason AS "spamReason",
                pr.review_window_expires_at AS "reviewWindowExpiresAt",
                pr.edited_at AS "editedAt",
                CASE
                    WHEN o.status = 'REFUNDED' THEN 'DA_HOAN_TIEN'
                    WHEN o.status = 'RETURNED' THEN 'DA_TRA_HANG'
                    ELSE NULL
                END AS "orderOutcome",
                pr.created_at AS "createdAt"
            FROM product_reviews pr
            JOIN products p ON p.id = pr.product_id
            LEFT JOIN orders o ON o.id = pr.order_id
            ORDER BY pr.created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.get("/reviews/summary", dependencies=[Depends(require_permission("review:read"))])
async def list_admin_review_summary(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                p.id::text AS "productId",
                p.name AS "productName",
                COUNT(pr.id) AS "totalReviews",
                COALESCE(p.review_count, 0) AS "publishedReviews",
                COUNT(*) FILTER (WHERE pr.status = 'PENDING') AS "pendingReviews",
                COUNT(*) FILTER (WHERE pr.flagged_reason IS NOT NULL) AS "flaggedReviews",
                p.rating AS "averageRating"
            FROM products p
            JOIN product_reviews pr ON pr.product_id = p.id
            GROUP BY p.id, p.name, p.rating, p.review_count
            ORDER BY "averageRating" DESC NULLS LAST, "totalReviews" DESC, p.name
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.patch("/reviews/{review_id}", dependencies=[Depends(require_permission("review:update"))])
async def update_review_status(review_id: UUID, payload: ReviewStatusPayload, session: AsyncSession = Depends(get_session)) -> dict:
    review_row = (
        await session.execute(
            text(
                """
                SELECT
                    pr.product_id,
                    pr.user_id,
                    pr.status,
                    p.name AS product_name
                FROM product_reviews pr
                JOIN products p ON p.id = pr.product_id
                WHERE pr.id = :id
                """
            ),
            {"id": review_id},
        )
    ).mappings().one_or_none()
    if not review_row:
        raise HTTPException(status_code=404, detail="Review not found.")

    updates: list[str] = []
    params: dict[str, object] = {"id": review_id}

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
    result = await session.execute(
        text(f"UPDATE product_reviews SET {', '.join(updates)} WHERE id = :id"),
        params,
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Review not found.")

    next_status = payload.status
    if (
        next_status in {"PUBLISHED", "REJECTED"}
        and next_status != review_row["status"]
        and review_row["user_id"] is not None
    ):
        notification_copy = {
            "PUBLISHED": (
                "Đánh giá đã được duyệt",
                f"Đánh giá của bạn cho sản phẩm {review_row['product_name']} đã được hiển thị công khai.",
            ),
            "REJECTED": (
                "Đánh giá chưa được duyệt",
                f"Đánh giá của bạn cho sản phẩm {review_row['product_name']} chưa được duyệt. Vui lòng kiểm tra nội dung và gửi lại nếu cần.",
            ),
        }[next_status]
        await session.execute(
            text(
                """
                INSERT INTO notifications (user_id, type, title, message)
                VALUES (:user_id, 'review', :title, :message)
                """
            ),
            {
                "user_id": review_row["user_id"],
                "title": notification_copy[0],
                "message": notification_copy[1],
            },
        )

    await sync_product_review_stats(session=session, product_id=review_row["product_id"])
    await session.commit()
    return {"ok": True}


@router.delete("/reviews/{review_id}", dependencies=[Depends(require_permission("review:delete"))])
async def delete_review(review_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    product_id = await session.scalar(text("SELECT product_id FROM product_reviews WHERE id = :id"), {"id": review_id})
    if not product_id:
        raise HTTPException(status_code=404, detail="Review not found.")
    result = await session.execute(text("DELETE FROM product_reviews WHERE id = :id"), {"id": review_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Review not found.")
    await sync_product_review_stats(session=session, product_id=product_id)
    await session.commit()
    return {"ok": True}


