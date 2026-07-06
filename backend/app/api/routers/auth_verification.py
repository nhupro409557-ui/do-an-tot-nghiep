from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models import User
from app.infrastructure.database.repositories import auth_repo
from app.infrastructure.database.session import get_session

from app.api.routers.auth_utils import (
    pwd_context,
    RegisterRequest,
    StartVerificationResponse,
    VerifyRegistrationRequest,
    ResendRegistrationRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    VerifyPasswordResetRequest,
    VerifyPasswordResetResponse,
    ResendPasswordResetRequest,
    ResetPasswordRequest,
    AuthResponse,
    ensure_auth_verification_tables,
    enforce_rate_limit,
    rate_limit_key,
    make_six_digit_code,
    send_auth_email,
    customer_role_id,
    issue_auth_response,
)

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Đăng ký trực tiếp đã tắt. Vui lòng dùng /auth/register/start và /auth/register/verify.",
    )


@router.post("/register/start", response_model=StartVerificationResponse)
async def start_registration(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> StartVerificationResponse:
    await ensure_auth_verification_tables(session)
    email = payload.email.lower()
    enforce_rate_limit(rate_limit_key(request, "register_start", email), limit=3, window_seconds=3600)
    if await auth_repo.user_exists_by_email(session, email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email này đã được đăng ký.")

    token = uuid4().hex
    code = make_six_digit_code()
    display_name = payload.displayName.strip()
    await auth_repo.delete_registration_token_by_email(session, email)
    await auth_repo.insert_registration_token(
        session,
        token=token,
        code=code,
        email=email,
        password_hash=pwd_context.hash(payload.password),
        display_name=display_name,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    await session.commit()
    send_auth_email(email, display_name, code, f"{settings.frontend_url}/verify-email?token={token}", "registration")
    return StartVerificationResponse(ok=True, email=email)


@router.post("/register/resend", response_model=StartVerificationResponse)
async def resend_registration(
    payload: ResendRegistrationRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> StartVerificationResponse:
    await ensure_auth_verification_tables(session)
    email = payload.email.lower()
    enforce_rate_limit(rate_limit_key(request, "register_resend", email), limit=3, window_seconds=3600)

    if await auth_repo.user_exists_by_email(session, email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email này đã được đăng ký.")

    pending = await auth_repo.get_registration_token_by_email_for_update(session, email)
    if pending is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy yêu cầu đăng ký đang chờ xác minh.")

    token = uuid4().hex
    code = make_six_digit_code()
    await auth_repo.delete_registration_token_by_email(session, email)
    await auth_repo.insert_registration_token(
        session,
        token=token,
        code=code,
        email=email,
        password_hash=pending["password_hash"],
        display_name=pending["display_name"],
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    await session.commit()
    send_auth_email(email, pending["display_name"], code, f"{settings.frontend_url}/verify-email?token={token}", "registration")
    return StartVerificationResponse(ok=True, email=email)


@router.post("/register/verify", response_model=AuthResponse)
async def verify_registration(
    payload: VerifyRegistrationRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    await ensure_auth_verification_tables(session)
    identity = payload.email.lower() if payload.email else payload.token
    enforce_rate_limit(rate_limit_key(request, "register_verify", identity), limit=10, window_seconds=900)
    if not payload.token and not (payload.email and payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu mã xác nhận.")

    pending = await auth_repo.get_registration_token_for_verify(
        session,
        token=payload.token,
        email=payload.email.lower() if payload.email else None,
        code=payload.code,
    )
    if pending is None or pending["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mã xác nhận không hợp lệ hoặc đã hết hạn.")

    email = pending["email"]
    if await auth_repo.user_exists_by_email(session, email):
        await auth_repo.delete_registration_token_by_email(session, email)
        await session.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email này đã được đăng ký.")

    user = User(
        id=uuid4(),
        role_id=await customer_role_id(session),
        email=email,
        password_hash=pending["password_hash"],
        full_name=pending["display_name"],
        profile_json={"displayName": pending["display_name"], "tier": "S-New"},
        addresses=[],
    )
    await auth_repo.add_user(session, user)
    await auth_repo.delete_registration_token_by_email(session, email)
    from app.api.routers.auth_utils import sync_and_link_offline_orders
    await sync_and_link_offline_orders(session, user)
    await session.flush()
    return await issue_auth_response(session, response, request, user, event_type="register_verified")


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ForgotPasswordResponse:
    await ensure_auth_verification_tables(session)
    email = payload.email.lower()
    enforce_rate_limit(rate_limit_key(request, "forgot_password", email), limit=3, window_seconds=3600)
    user = await auth_repo.get_active_user_by_email(session, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài khoản với email này.")

    token = uuid4().hex
    verification_token = uuid4().hex
    code = make_six_digit_code()
    await auth_repo.delete_password_reset_by_email(session, email)
    await auth_repo.insert_password_reset_token(
        session,
        token=token,
        email=email,
        code=code,
        verification_token=verification_token,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    await session.commit()
    send_auth_email(email, user.full_name or email, code, f"{settings.frontend_url}/reset-password?verify={verification_token}", "password_reset")
    return ForgotPasswordResponse(ok=True, email=email)


@router.post("/forgot-password/resend", response_model=ForgotPasswordResponse)
async def resend_password_reset(
    payload: ResendPasswordResetRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ForgotPasswordResponse:
    await ensure_auth_verification_tables(session)
    email = payload.email.lower()
    enforce_rate_limit(rate_limit_key(request, "forgot_password_resend", email), limit=3, window_seconds=3600)

    user = await auth_repo.get_active_user_by_email(session, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài khoản với email này.")

    if await auth_repo.get_password_reset_by_email_for_update(session, email) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy yêu cầu đặt lại mật khẩu đang chờ xác minh.")

    token = uuid4().hex
    verification_token = uuid4().hex
    code = make_six_digit_code()
    await auth_repo.delete_password_reset_by_email(session, email)
    await auth_repo.insert_password_reset_token(
        session,
        token=token,
        email=email,
        code=code,
        verification_token=verification_token,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    await session.commit()
    send_auth_email(email, user.full_name or email, code, f"{settings.frontend_url}/reset-password?verify={verification_token}", "password_reset")
    return ForgotPasswordResponse(ok=True, email=email)


@router.post("/forgot-password/verify", response_model=VerifyPasswordResetResponse)
async def verify_password_reset(
    payload: VerifyPasswordResetRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> VerifyPasswordResetResponse:
    await ensure_auth_verification_tables(session)
    identity = payload.email.lower() if payload.email else payload.token
    enforce_rate_limit(rate_limit_key(request, "forgot_password_verify", identity), limit=10, window_seconds=900)
    if not payload.token and not (payload.email and payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu mã xác nhận.")

    reset = await auth_repo.get_password_reset_for_verify(
        session,
        token=payload.token,
        email=payload.email.lower() if payload.email else None,
        code=payload.code,
    )
    if reset is None or reset["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mã xác nhận không hợp lệ hoặc đã hết hạn.")
    return VerifyPasswordResetResponse(resetToken=reset["token"])


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    from app.api.routers.auth_utils import ensure_session_security_tables, audit_log
    
    await ensure_session_security_tables(session)
    enforce_rate_limit(rate_limit_key(request, "reset_password", payload.token), limit=5, window_seconds=900)
    reset = await auth_repo.get_password_reset_by_token_for_update(session, payload.token)
    if reset is None or reset["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Liên kết đặt lại mật khẩu đã hết hạn.")
    email = reset["email"]
    user = await auth_repo.get_active_user_by_email(session, email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài khoản.")
    user.password_hash = pwd_context.hash(payload.newPassword)
    await auth_repo.delete_password_reset_by_token(session, payload.token)
    await auth_repo.revoke_all_user_refresh_sessions(session, user.id)
    await auth_repo.upsert_auth_session_revocation(session, user_id=user.id, reason="password_reset")
    await audit_log(session, "password_reset", request, user_id=user.id, email=user.email)
    await session.commit()
    return {"ok": True}
