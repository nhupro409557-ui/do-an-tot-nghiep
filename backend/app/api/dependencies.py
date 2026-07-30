import json
from uuid import UUID

import hashlib

from fastapi import Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.cache import get_redis
from app.infrastructure.database.repositories import auth_repo
from app.infrastructure.database.session import get_session


async def _decode_bearer_user_id(
    request: Request,
    authorization: str | None,
    session: AsyncSession = Depends(get_session),
) -> UUID | None:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            subject = payload.get("sub")
            if subject:
                user_id = UUID(subject)
                if payload.get("typ") != "access":
                    raise ValueError("Invalid token type")
                expected_fingerprint = payload.get("fp")
                if expected_fingerprint:
                    fingerprint = hashlib.sha256(request.headers.get("user-agent", "").encode("utf-8")).hexdigest()
                    if fingerprint != expected_fingerprint:
                        raise ValueError("Token fingerprint mismatch")
                issued_at = payload.get("iat")
                revoked_after = await auth_repo.get_session_revoked_after(session, user_id)
                if revoked_after is not None and issued_at is not None:
                    if int(issued_at) <= int(revoked_after.timestamp()):
                        raise ValueError("Token has been revoked")
                return user_id
        except (JWTError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authenticated user context.",
            ) from exc

    return None


async def get_optional_current_user_id(
    request: Request,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> UUID | None:
    return await _decode_bearer_user_id(request, authorization, session)


async def get_current_user_id(
    request: Request,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> UUID:
    user_id = await _decode_bearer_user_id(request, authorization, session)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authenticated user context.",
        )
    return user_id


async def get_current_role_code(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> str:
    role = await auth_repo.get_active_user_role_code(session, current_user_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not active.")
    return role


def require_roles(*allowed_roles: str):
    async def checker(role: str = Depends(get_current_role_code)) -> str:
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác này.",
            )
        return role

    return checker


require_staff_or_admin = require_roles("STAFF_ADMIN", "SUPER_ADMIN")
require_admin = require_roles("SUPER_ADMIN")
require_super_admin = require_roles("SUPER_ADMIN")


async def get_user_permissions(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
    redis=Depends(get_redis),
) -> set[str]:
    role_code = await auth_repo.get_active_user_role_code(session, current_user_id)
    if role_code == "SUPER_ADMIN":
        # SUPER_ADMIN luôn có toàn quyền, kể cả khi migration quyền mới chưa được
        # gán vào role_permissions hoặc Redis còn giữ danh sách quyền cũ.
        return set(await auth_repo.list_all_permission_codes(session))
    cache_key = f"admin_permissions:{current_user_id}"
    try:
        cached = await redis.get(cache_key)
        if cached:
            return set(json.loads(cached))
    except Exception:
        cached = None

    permissions = set(await auth_repo.list_permissions_for_user(session, current_user_id))
    try:
        await redis.set(cache_key, json.dumps(sorted(permissions)), ex=15 * 60)
    except Exception:
        pass
    return permissions


def require_permission(permission_code: str):
    async def checker(permissions: set[str] = Depends(get_user_permissions)) -> str:
        if permission_code not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác này.",
            )
        return permission_code

    return checker
