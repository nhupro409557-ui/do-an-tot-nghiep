import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pyotp
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.auth_utils import (
    AdminMfaChallengeResponse,
    audit_log,
    decode_admin_mfa_token,
    enforce_rate_limit,
    ensure_session_security_tables,
    get_active_user,
    make_admin_mfa_token,
    rate_limit_key,
    role_code,
    send_auth_email,
    super_admin_ip_allowed,
)
from app.config import settings
from app.infrastructure.database.repositories import auth_repo
from app.infrastructure.database.session import get_session

router = APIRouter()
RECOVERY_CODE_MINUTES = 15
RECOVERY_MAX_ATTEMPTS = 5


class AdminMfaRecoveryStartResponse(BaseModel):
    ok: bool
    email: str
    recoveryToken: str


class AdminMfaRecoveryVerifyRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


def mask_email(email: str) -> str:
    mailbox, separator, domain = email.partition("@")
    if not separator:
        return "***"
    if len(mailbox) <= 4:
        visible = mailbox[:1] + "***"
    else:
        visible = mailbox[:2] + "***" + mailbox[-2:]
    return f"{visible}@{domain}"


def hash_mfa_recovery_code(user_id: UUID, code: str) -> str:
    payload = f"admin-mfa-recovery:{user_id}:{code}".encode("utf-8")
    return hmac.new(settings.jwt_secret_key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _decode_challenge(
    authorization: str | None,
    request: Request,
    *,
    expected_scope: str,
) -> tuple[UUID, str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu phiên xác thực quản trị.",
        )
    user_id, scope, challenge_jti = decode_admin_mfa_token(authorization.split(" ", 1)[1], request)
    if scope != expected_scope:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên khôi phục MFA không hợp lệ.",
        )
    return user_id, challenge_jti


async def _get_recovery_user(session: AsyncSession, request: Request, user_id: UUID):
    user = await get_active_user(session, user_id)
    current_role = await role_code(session, user.role_id)
    if current_role == "SUPER_ADMIN" and not super_admin_ip_allowed(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="IP hiện tại không được phép khôi phục MFA cho Super Admin.",
        )
    if not await auth_repo.list_permissions_for_user(session, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản này không còn quyền quản trị.",
        )
    return user


@router.post("/admin/mfa-recovery/start", response_model=AdminMfaRecoveryStartResponse)
async def start_admin_mfa_recovery(
    request: Request,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> AdminMfaRecoveryStartResponse:
    user_id, _ = _decode_challenge(
        authorization,
        request,
        expected_scope="mfa_verify",
    )
    user = await _get_recovery_user(session, request, user_id)
    enforce_rate_limit(
        rate_limit_key(request, "admin_mfa_recovery_start", str(user.id)),
        limit=3,
        window_seconds=3600,
    )

    code = f"{secrets.randbelow(900000) + 100000}"
    recovery_jti = uuid4().hex
    await auth_repo.replace_admin_mfa_recovery(
        session,
        user_id=user.id,
        challenge_jti=recovery_jti,
        code_hash=hash_mfa_recovery_code(user.id, code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=RECOVERY_CODE_MINUTES),
    )
    await audit_log(
        session,
        "admin_mfa_recovery_requested",
        request,
        user_id=user.id,
        email=user.email,
    )
    await session.commit()
    send_auth_email(user.email, user.full_name or user.email, code, None, "admin_mfa_recovery")
    return AdminMfaRecoveryStartResponse(
        ok=True,
        email=mask_email(user.email),
        recoveryToken=make_admin_mfa_token(
            user.id,
            "mfa_recovery",
            request,
            expires_minutes=RECOVERY_CODE_MINUTES,
            token_jti=recovery_jti,
        ),
    )


@router.post("/admin/mfa-recovery/verify", response_model=AdminMfaChallengeResponse)
async def verify_admin_mfa_recovery(
    payload: AdminMfaRecoveryVerifyRequest,
    request: Request,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> AdminMfaChallengeResponse:
    user_id, challenge_jti = _decode_challenge(
        authorization,
        request,
        expected_scope="mfa_recovery",
    )
    user = await _get_recovery_user(session, request, user_id)
    enforce_rate_limit(
        rate_limit_key(request, "admin_mfa_recovery_verify", str(user.id)),
        limit=RECOVERY_MAX_ATTEMPTS,
        window_seconds=15 * 60,
    )

    recovery = await auth_repo.get_admin_mfa_recovery_for_update(session, user.id)
    now = datetime.now(timezone.utc)
    is_usable = bool(
        recovery
        and recovery["challenge_jti"] == challenge_jti
        and recovery["consumed_at"] is None
        and recovery["expires_at"] >= now
        and int(recovery["attempt_count"]) < RECOVERY_MAX_ATTEMPTS
    )
    code_matches = bool(
        is_usable
        and hmac.compare_digest(
            str(recovery["code_hash"]),
            hash_mfa_recovery_code(user.id, payload.code),
        )
    )
    if not code_matches:
        if is_usable:
            await auth_repo.increment_admin_mfa_recovery_attempt(session, user.id)
        await audit_log(
            session,
            "admin_mfa_recovery_failed",
            request,
            user_id=user.id,
            email=user.email,
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mã khôi phục không hợp lệ hoặc đã hết hạn.",
        )

    secret = pyotp.random_base32()
    await ensure_session_security_tables(session)
    await auth_repo.consume_admin_mfa_recovery(session, user.id)
    await auth_repo.upsert_admin_mfa_secret(session, user_id=user.id, secret=secret)
    await auth_repo.revoke_all_user_refresh_sessions(session, user.id)
    await auth_repo.upsert_auth_session_revocation(session, user_id=user.id, reason="admin_mfa_recovery")
    await audit_log(
        session,
        "admin_mfa_recovery_verified",
        request,
        user_id=user.id,
        email=user.email,
    )
    await session.commit()
    return AdminMfaChallengeResponse(
        requiresMfaSetup=True,
        tempToken=make_admin_mfa_token(user.id, "mfa_setup", request),
        mfaSecret=secret,
        otpauthUrl=pyotp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name="ElectroMart Admin",
        ),
    )
