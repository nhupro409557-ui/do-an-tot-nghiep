from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
import hashlib
import random
import secrets
import smtplib
import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from jose import jwt
from passlib.context import CryptContext
import pyotp
from pydantic import BaseModel, EmailStr, Field
from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id
from app.config import settings
from app.infrastructure.cache import get_redis
from app.infrastructure.database.models import Role, User
from app.infrastructure.database.session import get_session


router = APIRouter(prefix="/auth", tags=["Auth"])
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
rate_limit_hits: dict[str, list[float]] = {}
admin_login_hits: dict[str, list[float]] = {}
admin_login_locks: dict[str, float] = {}


class UserResponse(BaseModel):
    uid: UUID
    email: EmailStr
    displayName: str
    emailVerified: bool = True
    isAnonymous: bool = False
    tenantId: str | None = None
    providerData: list[dict[str, str | None]]


class ProfileResponse(BaseModel):
    role: str
    tier: str
    points: int
    walletStatus: str
    marketingOptIn: bool
    addresses: list[dict] = Field(default_factory=list)
    displayName: str | None = None
    phone: str | None = None
    birthDate: str | None = None
    gender: str | None = None
    avatarUrl: str | None = None
    verificationRole: str | None = None
    verificationStatus: str | None = None
    schoolOrWorkplace: str | None = None
    verificationCode: str | None = None
    permissions: list[str] = Field(default_factory=list)


class AuthResponse(BaseModel):
    token: str
    user: UserResponse
    profile: ProfileResponse


class AdminMfaChallengeResponse(BaseModel):
    requiresMfa: bool = False
    requiresMfaSetup: bool = False
    tempToken: str
    mfaSecret: str | None = None
    otpauthUrl: str | None = None


class AdminMfaVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    displayName: str = Field(min_length=1)


class StartVerificationResponse(BaseModel):
    ok: bool
    email: EmailStr
    verificationToken: str


class VerifyRegistrationRequest(BaseModel):
    email: EmailStr | None = None
    code: str | None = None
    token: str | None = None


class ResendRegistrationRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    email: EmailStr
    name: str
    picture: str | None = None


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str = Field(min_length=6)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    ok: bool
    email: EmailStr
    verificationToken: str


class VerifyPasswordResetRequest(BaseModel):
    email: EmailStr | None = None
    code: str | None = None
    token: str | None = None


class VerifyPasswordResetResponse(BaseModel):
    resetToken: str


class ResendPasswordResetRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    newPassword: str = Field(min_length=6)


class ProfileUpdateRequest(BaseModel):
    data: dict


class ActiveSessionResponse(BaseModel):
    id: UUID
    current: bool
    userAgent: str | None = None
    ipAddress: str | None = None
    createdAt: datetime
    rotatedAt: datetime | None = None
    expiresAt: datetime


REFRESH_COOKIE_NAME = "emv_refresh_token"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 30
REFRESH_GRACE_SECONDS = 60


def make_six_digit_code() -> str:
    return f"{random.randint(100000, 999999)}"


def rate_limit_key(request: Request, scope: str, identity: str | None = None) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"{scope}:{identity or ''}:{ip}"


def enforce_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    now = time.time()
    recent = [hit for hit in rate_limit_hits.get(key, []) if now - hit < window_seconds]
    if len(recent) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Ban thao tac qua nhieu lan. Vui long thu lai sau.",
        )
    recent.append(now)
    rate_limit_hits[key] = recent


async def cleanup_expired_auth_tokens(session: AsyncSession) -> None:
    await session.execute(
        text("DELETE FROM registration_verification_tokens WHERE expires_at < NOW()")
    )
    await session.execute(text("DELETE FROM password_reset_tokens WHERE expires_at < NOW()"))


async def ensure_auth_verification_tables(session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS registration_verification_tokens (
                token TEXT PRIMARY KEY,
                code VARCHAR(6) NOT NULL,
                email VARCHAR(255) NOT NULL,
                password_hash TEXT NOT NULL,
                display_name VARCHAR(255) NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    await cleanup_expired_auth_tokens(session)


async def ensure_session_security_tables(session: AsyncSession) -> None:
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('emv_auth_security_tables'))"))
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS refresh_token_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                family_id UUID NOT NULL,
                user_agent TEXT,
                ip_address VARCHAR(80),
                expires_at TIMESTAMPTZ NOT NULL,
                revoked_at TIMESTAMPTZ,
                replaced_by UUID,
                grace_until TIMESTAMPTZ,
                replaced_by_token_hash TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                rotated_at TIMESTAMPTZ
            )
            """
        )
    )
    await session.execute(text("ALTER TABLE refresh_token_sessions ADD COLUMN IF NOT EXISTS grace_until TIMESTAMPTZ"))
    await session.execute(text("ALTER TABLE refresh_token_sessions ADD COLUMN IF NOT EXISTS replaced_by_token_hash TEXT"))
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS security_audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                event_type VARCHAR(80) NOT NULL,
                email VARCHAR(255),
                ip_address VARCHAR(80),
                user_agent TEXT,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
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
    await session.execute(text("DELETE FROM refresh_token_sessions WHERE expires_at < NOW()"))


async def ensure_admin_mfa_table(session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS admin_mfa_settings (
                user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                mfa_secret TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )


async def admin_mfa_row(session: AsyncSession, user_id: UUID) -> dict | None:
    await ensure_admin_mfa_table(session)
    row = (
        await session.execute(
            text("SELECT mfa_enabled, mfa_secret FROM admin_mfa_settings WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
    ).mappings().first()
    return dict(row) if row else None


def super_admin_ip_allowed(request: Request) -> bool:
    raw = settings.super_admin_ip_whitelist.strip()
    if not raw:
        return True
    allowed = {item.strip() for item in raw.split(",") if item.strip()}
    return request_ip(request) in allowed


def request_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


def request_fingerprint(request: Request) -> str:
    user_agent = request.headers.get("user-agent", "")
    # Keep token binding stable across mobile / carrier IP changes to avoid false logouts.
    return hashlib.sha256(user_agent.encode("utf-8")).hexdigest()


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=REFRESH_TOKEN_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/v1/auth")


async def audit_log(
    session: AsyncSession,
    event_type: str,
    request: Request,
    user_id: UUID | None = None,
    email: str | None = None,
    metadata: dict | None = None,
) -> None:
    await ensure_session_security_tables(session)
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs
                (user_id, event_type, email, ip_address, user_agent, metadata)
            VALUES
                (:user_id, :event_type, :email, :ip_address, :user_agent, CAST(:metadata AS jsonb))
            """
        ),
        {
            "user_id": user_id,
            "event_type": event_type,
            "email": email,
            "ip_address": request_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "metadata": __import__("json").dumps(metadata or {}),
        },
    )


async def store_refresh_session(session: AsyncSession, request: Request, user_id: UUID, family_id: UUID | None = None) -> str:
    await ensure_session_security_tables(session)
    raw_token = secrets.token_urlsafe(48)
    await session.execute(
        text(
            """
            INSERT INTO refresh_token_sessions
                (id, user_id, token_hash, family_id, user_agent, ip_address, expires_at)
            VALUES
                (:id, :user_id, :token_hash, :family_id, :user_agent, :ip_address, :expires_at)
            """
        ),
        {
            "id": uuid4(),
            "user_id": user_id,
            "token_hash": hash_refresh_token(raw_token),
            "family_id": family_id or uuid4(),
            "user_agent": request.headers.get("user-agent"),
            "ip_address": request_ip(request),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS),
        },
    )
    return raw_token


async def refresh_token_by_hash(session: AsyncSession, token_hash: str) -> str | None:
    result = await session.execute(
        text(
            """
            SELECT token_hash
            FROM refresh_token_sessions
            WHERE token_hash = :token_hash
              AND revoked_at IS NULL
              AND expires_at > NOW()
            """
        ),
        {"token_hash": token_hash},
    )
    return result.scalar_one_or_none()
    await session.execute(text("ALTER TABLE password_reset_tokens ADD COLUMN IF NOT EXISTS code VARCHAR(6)"))
    await session.execute(text("ALTER TABLE password_reset_tokens ADD COLUMN IF NOT EXISTS verification_token TEXT"))
    await session.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_password_reset_tokens_verification_token
            ON password_reset_tokens(verification_token)
            """
        )
    )


def send_auth_email(email: str, name: str, code: str, link: str, purpose: str) -> None:
    if not settings.smtp_username or not settings.smtp_password:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SMTP is not configured.")

    sender = settings.smtp_from_email or settings.smtp_username
    brand_name = "ElectroMart VietNam"
    is_password_reset = purpose == "password_reset"
    action_name = "Dat lai mat khau" if is_password_reset else "Xac nhan tai khoan"
    intro = (
        f"Ban vua yeu cau dat lai mat khau tai khoan {brand_name}."
        if is_password_reset
        else f"Ban vua dang ky tai khoan {brand_name}."
    )

    message = EmailMessage()
    message["Subject"] = f"{action_name} {brand_name}"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                f"Xin chao {name},",
                "",
                intro,
                f"Ma xac nhan cua ban la: {code}",
                "",
                f"Hoac bam vao lien ket nay de xac nhan tu dong: {link}",
                "",
                "Ma xac nhan co hieu luc trong 15 phut.",
            ]
        )
    )
    message.add_alternative(
        f"""
        <div style="font-family:Arial,sans-serif;line-height:1.6;color:#111827">
          <h2 style="color:#d70018">{action_name} {brand_name}</h2>
          <p>Xin chao <strong>{name}</strong>,</p>
          <p>{intro}</p>
          <p>Ma xac nhan cua ban:</p>
          <div style="font-size:28px;font-weight:700;letter-spacing:6px;color:#d70018">{code}</div>
          <p>Hoac bam nut ben duoi de xac nhan tu dong:</p>
          <p>
            <a href="{link}" style="background:#d70018;color:#fff;text-decoration:none;padding:12px 18px;border-radius:8px;display:inline-block">
              {action_name}
            </a>
          </p>
          <p style="color:#6b7280;font-size:13px">Ma xac nhan co hieu luc trong 15 phut.</p>
        </div>
        """,
        subtype="html",
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Khong gui duoc email xac nhan.") from exc


def make_token(user_id: UUID, request: Request | None = None) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    payload = {
            "sub": str(user_id),
            "typ": "access",
            "jti": uuid4().hex,
            "iat": int(now.timestamp()),
            "exp": expires,
        }
    if request is not None:
        payload["fp"] = request_fingerprint(request)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def make_admin_mfa_token(user_id: UUID, scope: str, request: Request) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "typ": "admin_mfa",
            "scope": scope,
            "jti": uuid4().hex,
            "fp": request_fingerprint(request),
            "iat": int(now.timestamp()),
            "exp": now + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_admin_mfa_token(token: str, request: Request) -> tuple[UUID, str, str]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("typ") != "admin_mfa" or payload.get("fp") != request_fingerprint(request):
            raise ValueError("Invalid MFA token")
        return UUID(str(payload["sub"])), str(payload["scope"]), str(payload["jti"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên xác thực MFA không hợp lệ.") from exc


def to_user_response(user: User, provider: str = "password") -> UserResponse:
    return UserResponse(
        uid=user.id,
        email=user.email,
        displayName=user.full_name,
        providerData=[{"providerId": provider, "email": user.email}],
    )


async def role_code(session: AsyncSession, role_id: UUID) -> str:
    result = await session.execute(select(Role.code).where(Role.id == role_id))
    return result.scalar_one_or_none() or "CUSTOMER"


async def customer_role_id(session: AsyncSession) -> UUID:
    result = await session.execute(select(Role.id).where(Role.code == "CUSTOMER"))
    role_id = result.scalar_one_or_none()
    if role_id is None:
        role = Role(id=uuid4(), code="CUSTOMER", name="Customer")
        session.add(role)
        await session.flush()
        return role.id
    return role_id


async def to_profile_response(session: AsyncSession, user: User) -> ProfileResponse:
    role = await role_code(session, user.role_id)
    permissions = await list_permissions_for_user(session, user.id)
    profile = dict(user.profile_json or {})
    app_role = "staff" if role == "STAFF_ADMIN" else "user"
    if role == "SUPER_ADMIN":
        app_role = "super_admin"
    return ProfileResponse(
        role=app_role,
        tier=profile.get("tier") or user.loyalty_tier or "S-New",
        points=user.loyalty_points_balance,
        walletStatus=user.loyalty_wallet_status,
        marketingOptIn=user.marketing_opt_in,
        addresses=list(user.addresses or []),
        displayName=profile.get("displayName") or user.full_name,
        phone=profile.get("phone") or user.phone,
        birthDate=profile.get("birthDate"),
        gender=profile.get("gender"),
        avatarUrl=profile.get("avatarUrl"),
        verificationRole=profile.get("verificationRole"),
        verificationStatus=profile.get("verificationStatus"),
        schoolOrWorkplace=profile.get("schoolOrWorkplace"),
        verificationCode=profile.get("verificationCode"),
        permissions=permissions,
    )


async def list_permissions_for_user(session: AsyncSession, user_id: UUID) -> list[str]:
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
        {"user_id": user_id},
    )
    return [str(code) for code in result.scalars().all()]


def admin_login_key(request: Request, email: str) -> str:
    return f"admin_login:{email.lower()}:{request_ip(request)}"


async def assert_admin_login_not_locked(redis: Redis, key: str) -> None:
    try:
        ttl = await redis.ttl(f"{key}:locked")
    except Exception:
        locked_until = admin_login_locks.get(key, 0)
        ttl = int(locked_until - time.time()) if locked_until > time.time() else -1
        if ttl <= 0:
            admin_login_locks.pop(key, None)
    if ttl and ttl > 0:
        minutes = max(1, int((ttl + 59) / 60))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Tài khoản đã bị khóa tạm thời do đăng nhập sai nhiều lần. Vui lòng thử lại sau {minutes} phút.",
        )


async def record_admin_login_failed(
    session: AsyncSession,
    redis: Redis,
    key: str,
    request: Request,
    email: str,
) -> None:
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 15 * 60)
    except Exception:
        now = time.time()
        recent = [hit for hit in admin_login_hits.get(key, []) if now - hit < 15 * 60]
        recent.append(now)
        admin_login_hits[key] = recent
        count = len(recent)
    if count >= 5:
        try:
            await redis.setex(f"{key}:locked", 30 * 60, "1")
        except Exception:
            admin_login_locks[key] = time.time() + 30 * 60
        await audit_log(session, "admin_account_locked", request, email=email, metadata={"attempts": count})
    await audit_log(session, "admin_login_failed", request, email=email, metadata={"attempts": count})


async def clear_admin_login_failed(redis: Redis, key: str) -> None:
    try:
        await redis.delete(key)
        await redis.delete(f"{key}:locked")
    except Exception:
        pass
    admin_login_hits.pop(key, None)
    admin_login_locks.pop(key, None)


async def auth_payload(session: AsyncSession, user: User, provider: str = "password", request: Request | None = None) -> AuthResponse:
    return AuthResponse(token=make_token(user.id, request), user=to_user_response(user, provider), profile=await to_profile_response(session, user))


async def issue_auth_response(
    session: AsyncSession,
    response: Response,
    request: Request,
    user: User,
    provider: str = "password",
    event_type: str = "login_success",
) -> AuthResponse:
    refresh_token = await store_refresh_session(session, request, user.id)
    await audit_log(session, event_type, request, user_id=user.id, email=user.email, metadata={"provider": provider})
    await session.commit()
    set_refresh_cookie(response, refresh_token)
    await session.refresh(user)
    return await auth_payload(session, user, provider, request)


async def get_active_user(session: AsyncSession, user_id: UUID) -> User:
    result = await session.execute(select(User).where(User.id == user_id, User.status == "ACTIVE"))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not active.")
    return user


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


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    result = await session.execute(select(User).where(User.email == payload.email.lower(), User.status == "ACTIVE"))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(payload.password, user.password_hash):
        await audit_log(session, "login_failed", request, email=payload.email.lower())
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email hoac mat khau khong dung.")
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

    result = await session.execute(select(User).where(User.email == email, User.status == "ACTIVE"))
    user = result.scalar_one_or_none()
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
    if not mfa or not mfa.get("mfa_enabled") or not mfa.get("mfa_secret"):
        secret = pyotp.random_base32()
        await session.execute(
            text(
                """
                INSERT INTO admin_mfa_settings (user_id, mfa_enabled, mfa_secret)
                VALUES (:user_id, FALSE, :secret)
                ON CONFLICT (user_id)
                DO UPDATE SET mfa_secret = EXCLUDED.mfa_secret, updated_at = NOW()
                """
            ),
            {"user_id": user.id, "secret": secret},
        )
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
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="PhiÃªn MFA Ä‘Ã£ Ä‘Æ°á»£c sá»­ dá»¥ng.")
    except HTTPException:
        raise
    except Exception:
        pass
    user = await get_active_user(session, user_id)
    mfa = await admin_mfa_row(session, user.id)
    if not mfa or not mfa.get("mfa_secret"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA chưa được khởi tạo.")
    totp = pyotp.TOTP(str(mfa["mfa_secret"]))
    if not totp.verify(payload.code.strip(), valid_window=1):
        await audit_log(session, "admin_mfa_failed", request, user_id=user.id, email=user.email, metadata={"scope": scope})
        await session.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mã xác thực MFA không hợp lệ.")
    if scope == "mfa_setup":
        await session.execute(
            text("UPDATE admin_mfa_settings SET mfa_enabled = TRUE, updated_at = NOW() WHERE user_id = :user_id"),
            {"user_id": user.id},
        )
    elif scope != "mfa_verify":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên MFA không hợp lệ.")
    try:
        await redis.setex(used_token_key, 5 * 60, "1")
    except Exception:
        pass
    return await issue_auth_response(session, response, request, user, event_type="admin_mfa_success")


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


@router.get("/me", response_model=AuthResponse)
async def me(current_user_id: UUID = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)) -> AuthResponse:
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
    result = await session.execute(
        text(
            """
            SELECT id, user_id, family_id, expires_at, revoked_at, grace_until, user_agent, ip_address
            FROM refresh_token_sessions
            WHERE token_hash = :token_hash
            FOR UPDATE
            """
        ),
        {"token_hash": token_hash},
    )
    current = result.mappings().one_or_none()
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
    new_result = await session.execute(
        text("SELECT id FROM refresh_token_sessions WHERE token_hash = :token_hash"),
        {"token_hash": new_hash},
    )
    new_id = new_result.scalar_one()
    await session.execute(
        text(
            """
            UPDATE refresh_token_sessions
            SET revoked_at = NOW(),
                rotated_at = NOW(),
                replaced_by = :new_id,
                replaced_by_token_hash = :new_hash,
                grace_until = NOW() + make_interval(secs => :grace_seconds)
            WHERE id = :old_id
            """
        ),
        {"new_id": new_id, "new_hash": new_hash, "grace_seconds": REFRESH_GRACE_SECONDS, "old_id": current["id"]},
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
        await session.execute(
            text("UPDATE refresh_token_sessions SET revoked_at = NOW() WHERE token_hash = :token_hash"),
            {"token_hash": hash_refresh_token(refresh_token)},
        )
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
    result = await session.execute(
        text(
            """
            SELECT id, token_hash, user_agent, ip_address, created_at, rotated_at, expires_at
            FROM refresh_token_sessions
            WHERE user_id = :user_id
              AND revoked_at IS NULL
              AND expires_at > NOW()
            ORDER BY created_at DESC
            """
        ),
        {"user_id": current_user_id},
    )
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
        for row in result.mappings()
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
    result = await session.execute(
        text(
            """
            SELECT id, token_hash
            FROM refresh_token_sessions
            WHERE id = :session_id
              AND user_id = :user_id
              AND revoked_at IS NULL
              AND expires_at > NOW()
            FOR UPDATE
            """
        ),
        {"session_id": session_id, "user_id": current_user_id},
    )
    target = result.mappings().one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Khong tim thay phien dang nhap.")

    await session.execute(
        text("UPDATE refresh_token_sessions SET revoked_at = NOW() WHERE id = :session_id"),
        {"session_id": session_id},
    )
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mat khau hien tai khong dung.")
    user.password_hash = pwd_context.hash(payload.newPassword)
    await session.execute(text("UPDATE refresh_token_sessions SET revoked_at = NOW() WHERE user_id = :user_id"), {"user_id": user.id})
    await session.execute(
        text(
            """
            INSERT INTO auth_session_revocations (user_id, revoked_after, reason)
            VALUES (:user_id, NOW(), 'password_changed')
            ON CONFLICT (user_id)
            DO UPDATE SET revoked_after = EXCLUDED.revoked_after, reason = EXCLUDED.reason, created_at = NOW()
            """
        ),
        {"user_id": user.id},
    )
    await audit_log(session, "password_changed", request, user_id=user.id, email=user.email)
    await session.commit()
    return {"ok": True}


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
