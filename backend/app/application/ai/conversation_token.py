from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt

from app.config import settings


TOKEN_TYPE = "ai_conversation"


def issue_conversation_token(
    *,
    conversation_id: UUID,
    user_id: UUID | None,
    ttl_minutes: int,
) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=max(1, ttl_minutes))
    payload = {
        "typ": TOKEN_TYPE,
        "cid": str(conversation_id),
        "uid": str(user_id) if user_id else None,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def validate_conversation_token(
    token: str,
    *,
    conversation_id: UUID,
    user_id: UUID | None,
) -> None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise ValueError("Phiên trò chuyện không hợp lệ hoặc đã hết hạn.") from exc

    expected_user_id = str(user_id) if user_id else None
    if (
        payload.get("typ") != TOKEN_TYPE
        or payload.get("cid") != str(conversation_id)
        or payload.get("uid") != expected_user_id
    ):
        raise ValueError("Phiên trò chuyện không thuộc người dùng hiện tại.")
