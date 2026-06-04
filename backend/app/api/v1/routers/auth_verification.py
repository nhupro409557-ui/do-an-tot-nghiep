from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models import User
from app.infrastructure.database.session import get_session

from app.api.v1.routers.auth_utils import (
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
        detail="Dang ky truc tiep da tat. Vui long dung /auth/register/start va /auth/register/verify.",
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
    existing = await session.execute(select(User).where(User.email == email, User.status != "DELETED"))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email nay da duoc dang ky.")

    token = uuid4().hex
    code = make_six_digit_code()
    display_name = payload.displayName.strip()
    await session.execute(text("DELETE FROM registration_verification_tokens WHERE email = :email"), {"email": email})
    await session.execute(
        text(
            """
            INSERT INTO registration_verification_tokens
                (token, code, email, password_hash, display_name, expires_at)
            VALUES
                (:token, :code, :email, :password_hash, :display_name, :expires_at)
            """
        ),
        {
            "token": token,
            "code": code,
            "email": email,
            "password_hash": pwd_context.hash(payload.password),
            "display_name": display_name,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
    )
    await session.commit()
    send_auth_email(email, display_name, code, f"{settings.frontend_url}/verify-email?token={token}", "registration")
    return StartVerificationResponse(ok=True, email=email, verificationToken=token)


@router.post("/register/resend", response_model=StartVerificationResponse)
async def resend_registration(
    payload: ResendRegistrationRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> StartVerificationResponse:
    await ensure_auth_verification_tables(session)
    email = payload.email.lower()
    enforce_rate_limit(rate_limit_key(request, "register_resend", email), limit=3, window_seconds=3600)

    existing = await session.execute(select(User).where(User.email == email, User.status != "DELETED"))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email nay da duoc dang ky.")

    result = await session.execute(
        text(
            """
            SELECT email, password_hash, display_name
            FROM registration_verification_tokens
            WHERE email = :email
            FOR UPDATE
            """
        ),
        {"email": email},
    )
    pending = result.mappings().one_or_none()
    if pending is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khong tim thay yeu cau dang ky dang cho xac minh.")

    token = uuid4().hex
    code = make_six_digit_code()
    await session.execute(text("DELETE FROM registration_verification_tokens WHERE email = :email"), {"email": email})
    await session.execute(
        text(
            """
            INSERT INTO registration_verification_tokens
                (token, code, email, password_hash, display_name, expires_at)
            VALUES
                (:token, :code, :email, :password_hash, :display_name, :expires_at)
            """
        ),
        {
            "token": token,
            "code": code,
            "email": email,
            "password_hash": pending["password_hash"],
            "display_name": pending["display_name"],
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
    )
    await session.commit()
    send_auth_email(email, pending["display_name"], code, f"{settings.frontend_url}/verify-email?token={token}", "registration")
    return StartVerificationResponse(ok=True, email=email, verificationToken=token)


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thieu ma xac nhan.")

    if payload.token:
        result = await session.execute(
            text("SELECT * FROM registration_verification_tokens WHERE token = :token FOR UPDATE"),
            {"token": payload.token},
        )
    else:
        result = await session.execute(
            text(
                """
                SELECT * FROM registration_verification_tokens
                WHERE email = :email AND code = :code
                FOR UPDATE
                """
            ),
            {"email": payload.email.lower(), "code": payload.code},
        )
    pending = result.mappings().one_or_none()
    if pending is None or pending["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ma xac nhan khong hop le hoac da het han.")

    email = pending["email"]
    existing = await session.execute(select(User).where(User.email == email, User.status != "DELETED"))
    if existing.scalar_one_or_none():
        await session.execute(text("DELETE FROM registration_verification_tokens WHERE email = :email"), {"email": email})
        await session.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email nay da duoc dang ky.")

    user = User(
        id=uuid4(),
        role_id=await customer_role_id(session),
        email=email,
        password_hash=pending["password_hash"],
        full_name=pending["display_name"],
        profile_json={"displayName": pending["display_name"], "tier": "S-New"},
        addresses=[],
    )
    session.add(user)
    await session.execute(text("DELETE FROM registration_verification_tokens WHERE email = :email"), {"email": email})
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
    result = await session.execute(select(User).where(User.email == email, User.status == "ACTIVE"))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khong tim thay tai khoan voi email nay.")

    token = uuid4().hex
    verification_token = uuid4().hex
    code = make_six_digit_code()
    await session.execute(text("DELETE FROM password_reset_tokens WHERE email = :email"), {"email": email})
    await session.execute(
        text(
            """
            INSERT INTO password_reset_tokens (token, email, code, verification_token, expires_at)
            VALUES (:token, :email, :code, :verification_token, :expires_at)
            """
        ),
        {
            "token": token,
            "email": email,
            "code": code,
            "verification_token": verification_token,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
        },
    )
    await session.commit()
    send_auth_email(email, user.full_name or email, code, f"{settings.frontend_url}/reset-password?verify={verification_token}", "password_reset")
    return ForgotPasswordResponse(ok=True, email=email, verificationToken=verification_token)


@router.post("/forgot-password/resend", response_model=ForgotPasswordResponse)
async def resend_password_reset(
    payload: ResendPasswordResetRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ForgotPasswordResponse:
    await ensure_auth_verification_tables(session)
    email = payload.email.lower()
    enforce_rate_limit(rate_limit_key(request, "forgot_password_resend", email), limit=3, window_seconds=3600)

    user_result = await session.execute(select(User).where(User.email == email, User.status == "ACTIVE"))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khong tim thay tai khoan voi email nay.")

    result = await session.execute(
        text(
            """
            SELECT email FROM password_reset_tokens
            WHERE email = :email
            FOR UPDATE
            """
        ),
        {"email": email},
    )
    if result.mappings().one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khong tim thay yeu cau dat lai mat khau dang cho xac minh.")

    token = uuid4().hex
    verification_token = uuid4().hex
    code = make_six_digit_code()
    await session.execute(text("DELETE FROM password_reset_tokens WHERE email = :email"), {"email": email})
    await session.execute(
        text(
            """
            INSERT INTO password_reset_tokens (token, email, code, verification_token, expires_at)
            VALUES (:token, :email, :code, :verification_token, :expires_at)
            """
        ),
        {
            "token": token,
            "email": email,
            "code": code,
            "verification_token": verification_token,
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
        },
    )
    await session.commit()
    send_auth_email(email, user.full_name or email, code, f"{settings.frontend_url}/reset-password?verify={verification_token}", "password_reset")
    return ForgotPasswordResponse(ok=True, email=email, verificationToken=verification_token)


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thieu ma xac nhan.")

    if payload.token:
        result = await session.execute(
            text(
                """
                SELECT token, expires_at FROM password_reset_tokens
                WHERE verification_token = :token
                FOR UPDATE
                """
            ),
            {"token": payload.token},
        )
    else:
        result = await session.execute(
            text(
                """
                SELECT token, expires_at FROM password_reset_tokens
                WHERE email = :email AND code = :code
                FOR UPDATE
                """
            ),
            {"email": payload.email.lower(), "code": payload.code},
        )
    reset = result.mappings().one_or_none()
    if reset is None or reset["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ma xac nhan khong hop le hoac da het han.")
    return VerifyPasswordResetResponse(resetToken=reset["token"])


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    from app.api.v1.routers.auth_utils import ensure_session_security_tables, audit_log
    
    await ensure_session_security_tables(session)
    enforce_rate_limit(rate_limit_key(request, "reset_password", payload.token), limit=5, window_seconds=900)
    reset_result = await session.execute(
        text(
            """
            SELECT email, expires_at FROM password_reset_tokens
            WHERE token = :token
            FOR UPDATE
            """
        ),
        {"token": payload.token},
    )
    reset = reset_result.mappings().one_or_none()
    if reset is None or reset["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lien ket dat lai mat khau da het han.")
    email = reset["email"]
    result = await session.execute(select(User).where(User.email == email, User.status == "ACTIVE"))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khong tim thay tai khoan.")
    user.password_hash = pwd_context.hash(payload.newPassword)
    await session.execute(text("DELETE FROM password_reset_tokens WHERE token = :token"), {"token": payload.token})
    await session.execute(text("UPDATE refresh_token_sessions SET revoked_at = NOW() WHERE user_id = :user_id"), {"user_id": user.id})
    await session.execute(
        text(
            """
            INSERT INTO auth_session_revocations (user_id, revoked_after, reason)
            VALUES (:user_id, NOW(), 'password_reset')
            ON CONFLICT (user_id)
            DO UPDATE SET revoked_after = EXCLUDED.revoked_after, reason = EXCLUDED.reason, created_at = NOW()
            """
        ),
        {"user_id": user.id},
    )
    await audit_log(session, "password_reset", request, user_id=user.id, email=user.email)
    await session.commit()
    return {"ok": True}
