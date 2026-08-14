import hashlib
import html
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
from sqlalchemy import text
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
    birthDateLocked: bool = False
    gender: str | None = None
    avatarUrl: str | None = None
    verificationRole: str | None = None
    verificationStatus: str | None = None
    schoolOrWorkplace: str | None = None
    verificationCode: str | None = None
    permissions: list[str] = Field(default_factory=list)
    tierPeriodStartedAt: str | None = None
    tierPeriodEndsAt: str | None = None
    tierPeriodSpendAmount: int = 0
    pointsExpiringSoon: int = 0
    nearestPointsExpirationAt: str | None = None
    nearestPointsExpirationAmount: int = 0

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
    credential: str | None = Field(default=None, min_length=20, max_length=4096)
    id_token: str | None = Field(default=None, min_length=20, max_length=4096)
    access_token: str | None = Field(default=None, min_length=20, max_length=4096)

class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str = Field(min_length=6)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    ok: bool
    email: EmailStr
    adminContext: bool = False

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

def send_auth_email(email: str, name: str, code: str, link: str | None, purpose: str) -> None:
    if not settings.smtp_username or not settings.smtp_password:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="SMTP chưa được cấu hình.")

    sender = settings.smtp_from_email or settings.smtp_username
    brand_name = "ElectroMart VietNam"
    is_password_reset = purpose == "password_reset"
    is_mfa_recovery = purpose == "admin_mfa_recovery"
    if is_mfa_recovery:
        action_name = "Khôi phục mã 2FA quản trị"
        intro = f"Bạn vừa yêu cầu thiết lập lại mã 2FA cho tài khoản quản trị {brand_name}."
    elif is_password_reset:
        action_name = "Đặt lại mật khẩu"
        intro = f"Bạn vừa yêu cầu đặt lại mật khẩu tài khoản {brand_name}."
    else:
        action_name = "Xác nhận tài khoản"
        intro = f"Bạn vừa yêu cầu đăng ký tài khoản {brand_name}."
    valid_minutes = 30 if is_password_reset else 15
    warning_text = (
        "Nếu bạn không thực hiện yêu cầu này, hãy đổi mật khẩu ngay."
        if is_password_reset or is_mfa_recovery
        else "Nếu bạn không thực hiện yêu cầu này, bạn có thể bỏ qua email."
    )

    safe_name = html.escape(name)
    safe_link = html.escape(link or "", quote=True)
    link_text = f"Hoặc mở liên kết này để xác nhận tự động: {link}" if link else ""
    link_html = (
        f"""
          <p>Hoặc bấm nút bên dưới để xác nhận tự động:</p>
          <p>
            <a href="{safe_link}" style="background:#d70018;color:#fff;text-decoration:none;padding:12px 18px;border-radius:8px;display:inline-block">
              {action_name}
            </a>
          </p>
        """
        if link
        else ""
    )

    message = EmailMessage()
    message["Subject"] = f"{action_name} {brand_name}"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                f"Xin chào {name},",
                "",
                intro,
                f"Mã xác nhận của bạn là: {code}",
                "",
                link_text,
                "",
                f"Mã xác nhận có hiệu lực trong {valid_minutes} phút.",
                warning_text,
            ]
        )
    )
    message.add_alternative(
        f"""
        <div style="font-family:Arial,sans-serif;line-height:1.6;color:#111827">
          <h2 style="color:#d70018">{action_name} {brand_name}</h2>
          <p>Xin chào <strong>{safe_name}</strong>,</p>
          <p>{intro}</p>
          <p>Mã xác nhận của bạn:</p>
          <div style="font-size:28px;font-weight:700;letter-spacing:6px;color:#d70018">{code}</div>
          {link_html}
          <p style="color:#6b7280;font-size:13px">Mã xác nhận có hiệu lực trong {valid_minutes} phút.</p>
          <p style="color:#6b7280;font-size:13px">{warning_text}</p>
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
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Không gửi được email xác nhận.") from exc

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

def make_admin_mfa_token(
    user_id: UUID,
    scope: str,
    request: Request,
    *,
    expires_minutes: int = 5,
    token_jti: str | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "typ": "admin_mfa",
            "scope": scope,
            "jti": token_jti or uuid4().hex,
            "fp": request_fingerprint(request),
            "iat": int(now.timestamp()),
            "exp": now + timedelta(minutes=expires_minutes),
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
    from app.application.services.loyalty_maintenance_service import expire_user_points
    synced_balance = await expire_user_points(session, user_id=user.id)
    if synced_balance is not None:
        user.loyalty_points_balance = synced_balance
        await session.commit()
    role = await role_code(session, user.role_id)
    permissions = await list_permissions_for_user(session, user.id)
    profile = dict(user.profile_json or {})
    app_role = "staff" if role == "STAFF_ADMIN" else "user"
    if role == "SUPER_ADMIN":
        app_role = "super_admin"
    loyalty_summary = (await session.execute(
        text(
            """
            SELECT
                COALESCE((
                    SELECT SUM(total_amount)
                    FROM orders
                    WHERE user_id = :user_id
                      AND status = 'COMPLETED'
                      AND completed_at >= :period_start
                      AND completed_at < :period_end
                ), 0)::bigint AS period_spend_amount,
                COALESCE((
                    SELECT SUM(remaining_points)
                    FROM loyalty_point_lots
                    WHERE user_id = :user_id
                      AND remaining_points > 0
                      AND expired_at IS NULL
                      AND expires_at > NOW()
                      AND expires_at <= NOW() + INTERVAL '30 days'
                ), 0)::integer AS expiring_soon
            """
        ),
        {
            "user_id": user.id,
            "period_start": user.loyalty_tier_period_started_at,
            "period_end": user.loyalty_tier_period_ends_at,
        },
    )).mappings().one()
    nearest_expiration = (await session.execute(
        text(
            """
            SELECT expires_at, SUM(remaining_points)::integer AS points
            FROM loyalty_point_lots
            WHERE user_id = :user_id
              AND remaining_points > 0
              AND expired_at IS NULL
              AND expires_at > NOW()
            GROUP BY expires_at
            ORDER BY expires_at
            LIMIT 1
            """
        ),
        {"user_id": user.id},
    )).mappings().first()
    return ProfileResponse(
        role=app_role,
        tier=user.loyalty_tier or profile.get("tier") or "MEMBER",
        points=user.loyalty_points_balance,
        walletStatus=user.loyalty_wallet_status,
        marketingOptIn=user.marketing_opt_in,
        addresses=list(user.addresses or []),
        displayName=profile.get("displayName") or user.full_name,
        phone=profile.get("phone") or user.phone,
        birthDate=user.birth_date.isoformat() if user.birth_date else profile.get("birthDate"),
        birthDateLocked=bool(user.birth_date_locked_at or user.birth_date),
        gender=profile.get("gender"),
        avatarUrl=profile.get("avatarUrl"),
        verificationRole=profile.get("verificationRole"),
        verificationStatus=profile.get("verificationStatus"),
        schoolOrWorkplace=profile.get("schoolOrWorkplace"),
        verificationCode=profile.get("verificationCode"),
        permissions=permissions,
        tierPeriodStartedAt=user.loyalty_tier_period_started_at.isoformat() if user.loyalty_tier_period_started_at else None,
        tierPeriodEndsAt=user.loyalty_tier_period_ends_at.isoformat() if user.loyalty_tier_period_ends_at else None,
        tierPeriodSpendAmount=int(loyalty_summary["period_spend_amount"] or 0),
        pointsExpiringSoon=int(loyalty_summary["expiring_soon"] or 0),
        nearestPointsExpirationAt=nearest_expiration["expires_at"].isoformat() if nearest_expiration else None,
        nearestPointsExpirationAmount=int(nearest_expiration["points"] or 0) if nearest_expiration else 0,
    )

async def list_permissions_for_user(session: AsyncSession, user_id: UUID) -> list[str]:
    return await auth_repo.list_permissions_for_user(session, user_id)


async def assert_standard_login_allowed(
    session: AsyncSession,
    request: Request,
    user: User,
    *,
    provider: str,
) -> None:
    if not await list_permissions_for_user(session, user.id):
        return
    await audit_log(
        session,
        "admin_login_bypass_blocked",
        request,
        user_id=user.id,
        email=user.email,
        metadata={"provider": provider},
    )
    await session.commit()
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Tài khoản quản trị phải đăng nhập tại trang Admin và hoàn tất xác thực 2FA.",
    )

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
            await redis.set(f"{key}:locked", "1", ex=30 * 60)
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


async def sync_and_link_offline_orders(session: AsyncSession, user: User) -> None:
    from sqlalchemy import text
    from app.application.services.loyalty_maintenance_service import tier_from_spend
    from app.infrastructure.database.models import LoyaltyTransaction
    
    email = user.email.lower()
    # 1. Tìm đơn hàng offline gần nhất của email này để lấy họ tên và số điện thoại bổ sung cho profile
    order_info_res = await session.execute(
        text("""
            SELECT recipient_name, recipient_phone 
            FROM orders 
            WHERE user_id IS NULL AND recipient_email = :email 
            ORDER BY created_at DESC 
            LIMIT 1
        """),
        {"email": email}
    )
    order_info = order_info_res.mappings().first()
    if order_info:
        if order_info["recipient_name"] and not user.full_name:
            user.full_name = order_info["recipient_name"]
            profile = dict(user.profile_json or {})
            profile.update({"displayName": order_info["recipient_name"]})
            user.profile_json = profile
        if order_info["recipient_phone"] and not user.phone:
            user.phone = order_info["recipient_phone"]

    # 2. Tự động liên kết các đơn hàng cũ bằng email
    await session.execute(
        text("UPDATE orders SET user_id = :user_id WHERE user_id IS NULL AND recipient_email = :email"),
        {"user_id": user.id, "email": email}
    )

    # 3. Cộng dồn điểm Loyalty thưởng từ các đơn hàng offline cũ
    points_res = await session.execute(
        text("SELECT COALESCE(SUM(loyalty_points_earned), 0) FROM orders WHERE user_id = :user_id"),
        {"user_id": user.id}
    )
    total_points = int(points_res.scalar() or 0)
    if total_points > 0:
        user.loyalty_points_balance = total_points

        period_spend = await session.scalar(
            text(
                """
                SELECT COALESCE(SUM(total_amount), 0)
                FROM orders
                WHERE user_id = :user_id
                  AND status = 'COMPLETED'
                  AND completed_at >= :period_start
                  AND completed_at < :period_end
                """
            ),
            {
                "user_id": user.id,
                "period_start": user.loyalty_tier_period_started_at,
                "period_end": user.loyalty_tier_period_ends_at,
            },
        )
        user.loyalty_tier = tier_from_spend(period_spend or 0)
        
        # Thêm LoyaltyTransaction
        session.add(
            LoyaltyTransaction(
                id=uuid4(),
                user_id=user.id,
                type="EARN",
                points=total_points,
                balance_before=0,
                balance_after=total_points,
                reason="Đồng bộ điểm tích lũy tích được từ các đơn hàng mua tại quầy.",
                metadata_json={"linked_email": email},
            )
        )
    await session.flush()
