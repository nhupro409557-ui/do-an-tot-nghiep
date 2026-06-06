from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_admin_reviews(session: AsyncSession) -> list[dict]:
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


async def list_admin_review_summary(session: AsyncSession) -> list[dict]:
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


async def get_review_for_admin_update(session: AsyncSession, review_id: UUID) -> dict | None:
    row = (
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
    return dict(row) if row else None


async def update_review_fields(session: AsyncSession, review_id: UUID, updates: list[str], params: dict[str, object]) -> int:
    result = await session.execute(
        text(f"UPDATE product_reviews SET {', '.join(updates)} WHERE id = :id"),
        {"id": review_id, **params},
    )
    return int(result.rowcount or 0)


async def insert_review_notification(session: AsyncSession, *, user_id: UUID, title: str, message: str) -> None:
    await session.execute(
        text(
            """
            INSERT INTO notifications (user_id, type, title, message)
            VALUES (:user_id, 'review', :title, :message)
            """
        ),
        {"user_id": user_id, "title": title, "message": message},
    )


async def get_review_product_id(session: AsyncSession, review_id: UUID) -> UUID | None:
    return await session.scalar(text("SELECT product_id FROM product_reviews WHERE id = :id"), {"id": review_id})


async def delete_review(session: AsyncSession, review_id: UUID) -> int:
    result = await session.execute(text("DELETE FROM product_reviews WHERE id = :id"), {"id": review_id})
    return int(result.rowcount or 0)


async def count_recent_user_reviews(session: AsyncSession, *, user_id: UUID, window_minutes: int) -> int:
    count = await session.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM product_reviews
            WHERE user_id = :user_id
              AND created_at >= NOW() - make_interval(mins => :window_minutes)
            """
        ),
        {"user_id": user_id, "window_minutes": window_minutes},
    )
    return int(count or 0)


async def sync_product_review_stats(session: AsyncSession, product_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE products p
            SET
                rating = stats.rating,
                review_count = stats.review_count,
                updated_at = NOW()
            FROM (
                SELECT
                    :product_id AS product_id,
                    ROUND(AVG(rating) FILTER (WHERE status = 'PUBLISHED'), 2)::numeric(3, 2) AS rating,
                    COUNT(*) FILTER (WHERE status = 'PUBLISHED') AS review_count
                FROM product_reviews
                WHERE product_id = :product_id
            ) stats
            WHERE p.id = stats.product_id
            """
        ),
        {"product_id": product_id},
    )


async def get_latest_reviewable_order(session: AsyncSession, *, user_id: UUID, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    o.id::text AS id,
                    o.status,
                    o.payment_status AS "paymentStatus",
                    o.completed_at AS "completedAt",
                    o.refunded_at AS "refundedAt",
                    o.created_at AS "createdAt"
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE o.user_id = :user_id
                  AND oi.product_id = :product_id
                  AND o.payment_status = 'PAID'
                  AND o.status IN ('COMPLETED', 'RETURNED', 'REFUNDED')
                ORDER BY COALESCE(o.completed_at, o.created_at) DESC
                LIMIT 1
                """
            ),
            {"user_id": user_id, "product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None
