from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id
from app.infrastructure.cache import get_redis
from app.infrastructure.database.repositories import auth_repo
from app.infrastructure.database.session import get_session

from app.api.routers.auth_utils import (
    pwd_context,
    REFRESH_COOKIE_NAME,
    admin_login_key,
    assert_admin_login_not_locked,
    record_admin_login_failed,
    clear_admin_login_failed,
    admin_mfa_row,
    super_admin_ip_allowed,
    list_permissions_for_user,
    role_code,
    make_admin_mfa_token,
    decode_admin_mfa_token,
    get_active_user,
    issue_auth_response,
    auth_payload,
    hash_refresh_token,
    store_refresh_session,
    clear_refresh_cookie,
    set_refresh_cookie,
    ensure_session_security_tables,
    audit_log,
    AdminLoginRequest,
    AdminMfaChallengeResponse,
    AdminMfaVerifyRequest,
    LoginRequest,
    ActiveSessionResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    ChangePasswordRequest,
    AuthResponse,
    REFRESH_GRACE_SECONDS,
    request_ip,
)

from app.api.routers.auth_verification import router as verification_router
from app.api.routers.auth_social import router as social_router

router = APIRouter(prefix="/auth", tags=["Auth"])
router.include_router(verification_router)
router.include_router(social_router)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    user = await auth_repo.get_active_user_by_email(session, payload.email.lower())
    if not user or not pwd_context.verify(payload.password, user.password_hash):
        await audit_log(session, "login_failed", request, email=payload.email.lower())
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng.")
    return await issue_auth_response(session, response, request, user)


@router.post("/admin/login", response_model=AuthResponse | AdminMfaChallengeResponse)
async def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> AuthResponse | AdminMfaChallengeResponse:
    email = payload.email.lower()
    key = admin_login_key(request, email)
    await assert_admin_login_not_locked(redis, key)

    user = await auth_repo.get_active_user_by_email(session, email)
    if not user or not pwd_context.verify(payload.password, user.password_hash):
        await record_admin_login_failed(session, redis, key, request, email)
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng.")

    permissions = set(await list_permissions_for_user(session, user.id))
    if not permissions:
        await record_admin_login_failed(session, redis, key, request, email)
        await session.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản này không có quyền quản trị.")
    role = await role_code(session, user.role_id)
    if role == "SUPER_ADMIN" and not super_admin_ip_allowed(request):
        await audit_log(session, "admin_login_ip_blocked", request, user_id=user.id, email=email, metadata={"ip": request_ip(request)})
        await session.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="IP hiện tại không được phép đăng nhập Super Admin.")

    await clear_admin_login_failed(redis, key)
    mfa = await admin_mfa_row(session, user.id)
    import pyotp
    if not mfa or not mfa.get("mfa_enabled") or not mfa.get("mfa_secret"):
        secret = pyotp.random_base32()
        await auth_repo.upsert_admin_mfa_secret(session, user_id=user.id, secret=secret)
        await audit_log(session, "admin_mfa_setup_required", request, user_id=user.id, email=email)
        await session.commit()
        return AdminMfaChallengeResponse(
            requiresMfaSetup=True,
            tempToken=make_admin_mfa_token(user.id, "mfa_setup", request),
            mfaSecret=secret,
            otpauthUrl=pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="ElectroMart Admin"),
        )
    await audit_log(session, "admin_mfa_required", request, user_id=user.id, email=email)
    await session.commit()
    return AdminMfaChallengeResponse(
        requiresMfa=True,
        tempToken=make_admin_mfa_token(user.id, "mfa_verify", request),
    )


@router.post("/admin/verify-mfa", response_model=AuthResponse)
async def verify_admin_mfa(
    payload: AdminMfaVerifyRequest,
    request: Request,
    response: Response,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> AuthResponse:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Thiếu phiên xác thực MFA.")
    user_id, scope, token_jti = decode_admin_mfa_token(authorization.split(" ", 1)[1], request)
    used_token_key = f"admin_mfa_used:{token_jti}"
    try:
        if await redis.get(used_token_key):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên MFA đã được sử dụng.")
    except HTTPException:
        raise
    except Exception:
        pass
    user = await get_active_user(session, user_id)
    mfa = await admin_mfa_row(session, user.id)
    if not mfa or not mfa.get("mfa_secret"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA chưa được khởi tạo.")
    import pyotp
    totp = pyotp.TOTP(str(mfa["mfa_secret"]))
    if not totp.verify(payload.code.strip(), valid_window=1):
        await audit_log(session, "admin_mfa_failed", request, user_id=user.id, email=user.email, metadata={"scope": scope})
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mã xác thực MFA không hợp lệ.")
    if scope == "mfa_setup":
        await auth_repo.enable_admin_mfa(session, user.id)
    elif scope != "mfa_verify":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên MFA không hợp lệ.")
    try:
        await redis.setex(used_token_key, 5 * 60, "1")
    except Exception:
        pass
    return await issue_auth_response(session, response, request, user, event_type="admin_mfa_success")


@router.get("/me", response_model=AuthResponse)
async def me(
    request: Request,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
) -> AuthResponse:
    user = await get_active_user(session, current_user_id)
    return await auth_payload(session, user, request=request)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_session(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    await ensure_session_security_tables(session)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token.")

    token_hash = hash_refresh_token(refresh_token)
    current = await auth_repo.get_refresh_session_for_update(session, token_hash)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    is_grace_retry = False
    if current is not None and current["revoked_at"] is not None:
        same_client = current["ip_address"] == request_ip(request) and current["user_agent"] == request.headers.get("user-agent")
        is_grace_retry = bool(current["grace_until"] and current["grace_until"] >= now and same_client)
    if current is None or current["expires_at"] < now or (current["revoked_at"] is not None and not is_grace_retry):
        clear_refresh_cookie(response)
        await audit_log(session, "refresh_rejected", request, metadata={"reason": "invalid_or_expired"})
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

    user = await get_active_user(session, current["user_id"])
    if is_grace_retry:
        await audit_log(session, "refresh_grace_retry", request, user_id=user.id, email=user.email)
    new_refresh_token = await store_refresh_session(session, request, user.id, current["family_id"])
    new_hash = hash_refresh_token(new_refresh_token)
    new_id = await auth_repo.get_refresh_session_id_by_hash(session, new_hash)
    await auth_repo.rotate_refresh_session(
        session,
        old_session_id=current["id"],
        new_session_id=new_id,
        new_token_hash=new_hash,
        grace_seconds=REFRESH_GRACE_SECONDS,
    )
    await audit_log(session, "refresh_rotated", request, user_id=user.id, email=user.email)
    await session.commit()
    set_refresh_cookie(response, new_refresh_token)
    return await auth_payload(session, user)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    await ensure_session_security_tables(session)
    if refresh_token:
        await auth_repo.revoke_refresh_session_by_hash(session, hash_refresh_token(refresh_token))
    await audit_log(session, "logout", request)
    await session.commit()
    clear_refresh_cookie(response)
    return {"ok": True}


@router.get("/sessions", response_model=list[ActiveSessionResponse])
async def list_active_sessions(
    current_user_id: UUID = Depends(get_current_user_id),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    session: AsyncSession = Depends(get_session),
) -> list[ActiveSessionResponse]:
    await ensure_session_security_tables(session)
    current_hash = hash_refresh_token(refresh_token) if refresh_token else None
    await auth_repo.revoke_duplicate_active_refresh_sessions(session, current_user_id)
    await session.commit()
    rows = await auth_repo.list_active_refresh_sessions(session, current_user_id)
    return [
        ActiveSessionResponse(
            id=row["id"],
            current=row["token_hash"] == current_hash,
            userAgent=row["user_agent"],
            ipAddress=row["ip_address"],
            createdAt=row["created_at"],
            rotatedAt=row["rotated_at"],
            expiresAt=row["expires_at"],
        )
        for row in rows
    ]


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: UUID,
    request: Request,
    response: Response,
    current_user_id: UUID = Depends(get_current_user_id),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    await ensure_session_security_tables(session)
    current_hash = hash_refresh_token(refresh_token) if refresh_token else None
    target = await auth_repo.get_active_refresh_session_for_update(session, session_id=session_id, user_id=current_user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phiên đăng nhập.")

    await auth_repo.revoke_refresh_session_by_id(session, session_id)
    await audit_log(
        session,
        "session_revoked",
        request,
        user_id=current_user_id,
        metadata={"session_id": str(session_id), "current": target["token_hash"] == current_hash},
    )
    await session.commit()
    if target["token_hash"] == current_hash:
        clear_refresh_cookie(response)
    return {"ok": True}


@router.patch("/me/profile", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    user = await get_active_user(session, current_user_id)
    updates = dict(payload.data)
    profile = dict(user.profile_json or {})
    if "addresses" in updates:
        user.addresses = list(updates.pop("addresses") or [])
    profile.update(updates)
    if "displayName" in profile and profile["displayName"]:
        user.full_name = str(profile["displayName"])
    if "phone" in profile:
        user.phone = profile.get("phone") or None
    user.profile_json = profile
    await session.commit()
    await session.refresh(user)
    return await to_profile_response(session, user)


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    await ensure_session_security_tables(session)
    user = await get_active_user(session, current_user_id)
    if not pwd_context.verify(payload.currentPassword, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mật khẩu hiện tại không đúng.")
    user.password_hash = pwd_context.hash(payload.newPassword)
    await auth_repo.revoke_all_user_refresh_sessions(session, user.id)
    await auth_repo.upsert_auth_session_revocation(session, user_id=user.id, reason="password_changed")
    await audit_log(session, "password_changed", request, user_id=user.id, email=user.email)
    await session.commit()
    return {"ok": True}
