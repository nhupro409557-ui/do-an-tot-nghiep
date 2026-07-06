from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models import User
from app.infrastructure.database.repositories import auth_repo
from app.infrastructure.database.session import get_session

from app.api.routers.auth_utils import (
    pwd_context,
    GoogleLoginRequest,
    AuthResponse,
    customer_role_id,
    issue_auth_response,
)

router = APIRouter()


GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _google_client_ids() -> set[str]:
    return {item.strip() for item in settings.google_client_id.split(",") if item.strip()}


def _assert_google_audience(token_info: dict) -> None:
    allowed_client_ids = _google_client_ids()
    if not allowed_client_ids:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Login chưa được cấu hình ở backend.",
        )
    audience = str(token_info.get("aud") or token_info.get("issued_to") or token_info.get("azp") or "")
    if audience not in allowed_client_ids:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token không thuộc ứng dụng này.",
        )


def _assert_verified_google_email(profile: dict) -> str:
    email = str(profile.get("email") or "").strip().lower()
    email_verified = profile.get("email_verified")
    if isinstance(email_verified, str):
        email_verified = email_verified.lower() in {"true", "1", "yes"}
    if not email or email_verified is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google token không có email đã xác minh.",
        )
    return email


async def _verified_google_profile(payload: GoogleLoginRequest) -> dict:
    id_token = payload.credential or payload.id_token
    access_token = payload.access_token
    if not id_token and not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu Google ID token hoặc access token.",
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if id_token:
                token_response = await client.get(GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
                if token_response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Google ID token không hợp lệ.",
                    )
                token_info = token_response.json()
                _assert_google_audience(token_info)
                email = _assert_verified_google_email(token_info)
                return {
                    "email": email,
                    "name": str(token_info.get("name") or email),
                    "picture": token_info.get("picture"),
                }

            token_response = await client.get(GOOGLE_TOKENINFO_URL, params={"access_token": access_token})
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google access token không hợp lệ.",
                )
            token_info = token_response.json()
            _assert_google_audience(token_info)

            profile_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if profile_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Không đọc được hồ sơ Google từ token.",
                )
            profile = profile_response.json()
            email = _assert_verified_google_email(profile)
            return {
                "email": email,
                "name": str(profile.get("name") or email),
                "picture": profile.get("picture"),
            }
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Không thể xác minh Google token.",
        ) from exc


@router.post("/google", response_model=AuthResponse)
async def google_login(
    payload: GoogleLoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    profile = await _verified_google_profile(payload)
    email = profile["email"]
    user = await auth_repo.get_active_user_by_email(session, email)
    if user is None:
        user = User(
            id=uuid4(),
            role_id=await customer_role_id(session),
            email=email,
            password_hash=pwd_context.hash(uuid4().hex),
            full_name=profile["name"] or email,
            profile_json={"displayName": profile["name"] or email, "avatarUrl": profile["picture"], "tier": "S-New"},
            addresses=[],
        )
        await auth_repo.add_user(session, user)
        from app.api.routers.auth_utils import sync_and_link_offline_orders
        await sync_and_link_offline_orders(session, user)
    else:
        current_profile = dict(user.profile_json or {})
        current_profile.update({"displayName": profile["name"] or user.full_name, "avatarUrl": profile["picture"]})
        user.full_name = profile["name"] or user.full_name
        user.profile_json = current_profile
    await session.flush()
    return await issue_auth_response(session, response, request, user, "google", "google_login_success")
