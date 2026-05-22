import json
from uuid import UUID

import hashlib

from fastapi import Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session


async def get_current_user_id(
    request: Request,
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> UUID:
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
                await session.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS auth_session_revocations (
                            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                            revoked_after TIMESTAMPTZ NOT NULL,
                            reason VARCHAR(120) NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                )
                revoked = await session.execute(
                    text(
                        """
                        SELECT revoked_after
                        FROM auth_session_revocations
                        WHERE user_id = :user_id
                        """
                    ),
                    {"user_id": user_id},
                )
                revoked_after = revoked.scalar_one_or_none()
                if revoked_after is not None and issued_at is not None:
                    if int(issued_at) <= int(revoked_after.timestamp()):
                        raise ValueError("Token has been revoked")
                return user_id
        except (JWTError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authenticated user context.",
            ) from exc

    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authenticated user context.",
        )

    try:
        return UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authenticated user context.",
        ) from exc


async def get_current_role_code(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> str:
    result = await session.execute(
        text(
            """
            SELECT r.code
            FROM users u
            JOIN roles r ON r.id = u.role_id
            WHERE u.id = :user_id AND u.status = 'ACTIVE'
            """
        ),
        {"user_id": current_user_id},
    )
    role = result.scalar_one_or_none()
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
    cache_key = f"admin_permissions:{current_user_id}"
    try:
        cached = await redis.get(cache_key)
        if cached:
            return set(json.loads(cached))
    except Exception:
        cached = None

    result = await session.execute(
        text(
            """
            SELECT p.code
            FROM users u
            JOIN roles r ON r.id = u.role_id
            JOIN role_permissions rp ON rp.role_id = r.id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE u.id = :user_id
              AND u.status = 'ACTIVE'
            ORDER BY p.code
            """
        ),
        {"user_id": current_user_id},
    )
    permissions = {str(code) for code in result.scalars().all()}
    try:
        await redis.setex(cache_key, 15 * 60, json.dumps(sorted(permissions)))
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
