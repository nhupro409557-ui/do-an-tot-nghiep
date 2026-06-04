from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import User
from app.infrastructure.database.session import get_session

from app.api.v1.routers.auth_utils import (
    pwd_context,
    GoogleLoginRequest,
    AuthResponse,
    customer_role_id,
    issue_auth_response,
)

router = APIRouter()


@router.post("/google", response_model=AuthResponse)
async def google_login(
    payload: GoogleLoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    email = payload.email.lower()
    result = await session.execute(select(User).where(User.email == email, User.status == "ACTIVE"))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            id=uuid4(),
            role_id=await customer_role_id(session),
            email=email,
            password_hash=pwd_context.hash(uuid4().hex),
            full_name=payload.name or email,
            profile_json={"displayName": payload.name or email, "avatarUrl": payload.picture, "tier": "S-New"},
            addresses=[],
        )
        session.add(user)
    else:
        profile = dict(user.profile_json or {})
        profile.update({"displayName": payload.name or user.full_name, "avatarUrl": payload.picture})
        user.full_name = payload.name or user.full_name
        user.profile_json = profile
    await session.flush()
    return await issue_auth_response(session, response, request, user, "google", "google_login_success")
