import html
import json
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


REVIEW_WINDOW_DAYS = 30
REVIEW_RATE_LIMIT_COUNT = 3
REVIEW_RATE_LIMIT_MINUTES = 5


def normalize_review_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def sanitize_review_text(value: str) -> str:
    normalized = re.sub(r"<\s*/?\s*script[^>]*>", "", value, flags=re.IGNORECASE)
    normalized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", normalized)
    return html.escape(normalized.strip(), quote=False)


def sanitize_media_urls(media_urls: list[str], limit: int = 6) -> list[str]:
    cleaned = [item.strip() for item in media_urls if item and item.strip()]
    if len(cleaned) > limit:
        raise HTTPException(status_code=422, detail=f"Toi da {limit} anh/video cho moi danh gia.")
    if any(item.startswith("data:") for item in cleaned):
        raise HTTPException(status_code=400, detail="Media danh gia phai la URL da upload, khong dung data URL.")
    return cleaned


def detect_spam_reason(comment: str, media_urls: list[str]) -> str | None:
    normalized = normalize_review_text(comment)
    if len(set(normalized)) <= 3 and len(normalized) >= 12:
        return "Noi dung co dau hieu lap ky tu bat thuong."
    if re.search(r"(.)\1{7,}", normalized):
        return "Noi dung co chuoi ky tu lap lai qua nhieu."
    if normalized.count("http://") + normalized.count("https://") >= 2:
        return "Noi dung chua qua nhieu lien ket."
    if len(media_urls) > 4:
        return "Danh gia gan qua nhieu media trong mot lan gui."
    return None


async def enforce_review_rate_limit(*, session: AsyncSession, user_id: UUID) -> None:
    recent_count = await session.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM product_reviews
            WHERE user_id = :user_id
              AND created_at >= NOW() - make_interval(mins => :window_minutes)
            """
        ),
        {"user_id": user_id, "window_minutes": REVIEW_RATE_LIMIT_MINUTES},
    )
    if int(recent_count or 0) >= REVIEW_RATE_LIMIT_COUNT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Ban gui qua nhieu danh gia trong thoi gian ngan. Thu lai sau {REVIEW_RATE_LIMIT_MINUTES} phut.",
        )


async def sync_product_review_stats(*, session: AsyncSession, product_id: UUID) -> None:
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


async def get_latest_reviewable_order(*, session: AsyncSession, user_id: UUID, product_id: UUID) -> dict | None:
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


def compute_review_window(order_row: dict | None) -> tuple[bool, datetime | None]:
    if not order_row:
        return False, None
    completed_at = order_row.get("completedAt") or order_row.get("createdAt")
    if completed_at is None:
        return False, None
    if isinstance(completed_at, str):
        completed_at = datetime.fromisoformat(completed_at)
    expires_at = completed_at + timedelta(days=REVIEW_WINDOW_DAYS)
    return datetime.now(timezone.utc) <= expires_at, expires_at


def review_order_outcome_label(order_status: str | None) -> str | None:
    if order_status == "RETURNED":
        return "DA_TRA_HANG"
    if order_status == "REFUNDED":
        return "DA_HOAN_TIEN"
    return None


def dumps_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)
