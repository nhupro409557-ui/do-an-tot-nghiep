import html
import json
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import review_repo

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
        raise HTTPException(status_code=422, detail=f"Tối đa {limit} ảnh/video cho mỗi đánh giá.")
    if any(item.startswith("data:") for item in cleaned):
        raise HTTPException(status_code=400, detail="Media đánh giá phải là URL đã upload, không dùng data URL.")
    return cleaned


def detect_spam_reason(comment: str, media_urls: list[str]) -> str | None:
    normalized = normalize_review_text(comment)
    if len(set(normalized)) <= 3 and len(normalized) >= 12:
        return "Nội dung có dấu hiệu lặp ký tự bất thường."
    if re.search(r"(.)\1{7,}", normalized):
        return "Nội dung có chuỗi ký tự lặp lại quá nhiều."
    if normalized.count("http://") + normalized.count("https://") >= 2:
        return "Nội dung chứa quá nhiều liên kết."
    if len(media_urls) > 4:
        return "Đánh giá gắn quá nhiều media trong một lần gửi."
    return None


async def enforce_review_rate_limit(*, session: AsyncSession, user_id: UUID) -> None:
    recent_count = await review_repo.count_recent_user_reviews(
        session,
        user_id=user_id,
        window_minutes=REVIEW_RATE_LIMIT_MINUTES,
    )
    if recent_count >= REVIEW_RATE_LIMIT_COUNT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Bạn gửi quá nhiều đánh giá trong thời gian ngắn. Thử lại sau {REVIEW_RATE_LIMIT_MINUTES} phút.",
        )


async def sync_product_review_stats(*, session: AsyncSession, product_id: UUID) -> None:
    await review_repo.sync_product_review_stats(session, product_id)


async def get_latest_reviewable_order(*, session: AsyncSession, user_id: UUID, product_id: UUID) -> dict | None:
    return await review_repo.get_latest_reviewable_order(session, user_id=user_id, product_id=product_id)


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
