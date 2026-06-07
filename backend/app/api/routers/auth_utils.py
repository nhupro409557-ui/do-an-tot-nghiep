import hashlib
import random
import secrets
import smtplib
import time
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, Request, Response, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models import User
from app.infrastructure.database.repositories import auth_repo

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
rate_limit_hits: dict[str, list[float]] = {}
admin_login_hits: dict[str, list[float]] = {}
admin_login_locks: dict[str, float] = {}

REFRESH_COOKIE_NAME = "emv_refresh_token"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 30
REFRESH_GRACE_SECONDS = 60

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

def make_six_digit_code() -> str:
    return f"{random.randint(100000, 999999)}" if 'random' in globals() else f"{secrets.randbelow(900000) + 100000}"

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
    await auth_repo.cleanup_expired_auth_tokens(session)

async def ensure_auth_verification_tables(session: AsyncSession) -> None:
    await auth_repo.ensure_auth_verification_tables(session)

async def ensure_session_security_tables(session: AsyncSession) -> None:
    await auth_repo.ensure_session_security_tables(session)

async def ensure_admin_mfa_table(session: AsyncSession) -> None:
    await auth_repo.ensure_admin_mfa_table(session)

async def admin_mfa_row(session: AsyncSession, user_id: UUID) -> dict | None:
    return await auth_repo.get_admin_mfa_row(session, user_id)

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
        path="/api/auth",
    )

def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/auth")

async def audit_log(
    session: AsyncSession,
    event_type: str,
    request: Request,
    user_id: UUID | None = None,
    email: str | None = None,
    metadata: dict | None = None,
) -> None:
    await auth_repo.insert_security_audit_log(
        session,
        user_id=user_id,
        event_type=event_type,
        email=email,
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata=metadata or {},
    )

async def store_refresh_session(session: AsyncSession, request: Request, user_id: UUID, family_id: UUID | None = None) -> str:
    raw_token = secrets.token_urlsafe(48)
    await auth_repo.insert_refresh_session(
        session,
        session_id=uuid4(),
        user_id=user_id,
        token_hash=hash_refresh_token(raw_token),
        family_id=family_id or uuid4(),
        user_agent=request.headers.get("user-agent"),
        ip_address=request_ip(request),
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_DAYS),
    )
    return raw_token

async def refresh_token_by_hash(session: AsyncSession, token_hash: str) -> str | None:
    return await auth_repo.get_valid_refresh_token_hash(session, token_hash)

def send_auth_email(email: str, name: str, code: str, link: str, purpose: str) -> None:
    if not settings.smtp_username or not settings.smtp_password:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SMTP is not configured.")

    sender = settings.smtp_from_email or settings.smtp_username
    brand_name = "ElectroMart VietNam"
    is_password_reset = purpose == "password_reset"
    action_name = "Dat lai mat khau" if is_password_reset else "Xac nhan tai khoan"
    intro = (
        f"Ban yeu cau dat lai mat khau tai khoan {brand_name}."
        if is_password_reset
        else f"Ban yeu cau dang ky tai khoan {brand_name}."
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
    return await auth_repo.get_role_code(session, role_id) or "CUSTOMER"

async def customer_role_id(session: AsyncSession) -> UUID:
    role_id = await auth_repo.get_customer_role_id(session)
    if role_id is None:
        role_id = uuid4()
        await auth_repo.add_customer_role(session, role_id=role_id)
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
    return await auth_repo.list_permissions_for_user(session, user_id)

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
    user = await auth_repo.get_active_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not active.")
    return user
