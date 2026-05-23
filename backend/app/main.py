import json
import asyncio
import contextlib
from uuid import UUID

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from sqlalchemy import text

from app.api.v1.routers.ai_assistant import router as ai_assistant_router
from app.api.v1.routers.admin import router as admin_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.auth_email import router as auth_email_router
from app.api.v1.routers.catalog import router as catalog_router
from app.api.v1.routers.commerce import router as commerce_router
from app.api.v1.routers.content import router as content_router
from app.api.v1.routers.loyalty import router as loyalty_router
from app.api.v1.routers.storefront import router as storefront_router
from app.api.v1.routers.users import router as users_router
from app.application.commerce.use_cases import CompleteOrderUseCase
from app.config import settings
from app.infrastructure.database.session import AsyncSessionFactory


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    maintenance_task = None
    if settings.order_maintenance_enabled:
        maintenance_task = asyncio.create_task(run_order_maintenance_loop())
    try:
        yield
    finally:
        if maintenance_task is not None:
            maintenance_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await maintenance_task


app = FastAPI(
    title="Electronics Commerce API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Sửa chính xác thành như thế này bạn nhé
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SENSITIVE_AUDIT_KEYS = {"password", "token", "secret", "mfa_secret", "authorization", "refresh_token"}


def audit_request_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


def audit_actor_id(request) -> UUID | None:
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return None
    try:
        payload = jwt.decode(authorization.split(" ", 1)[1], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        subject = payload.get("sub")
        return UUID(subject) if subject else None
    except (JWTError, ValueError):
        return None


def resource_from_path(path: str) -> tuple[str | None, str | None]:
    parts = [part for part in path.split("/") if part]
    try:
        index = parts.index("admin")
    except ValueError:
        return None, None
    resource = parts[index + 1] if len(parts) > index + 1 else None
    resource_id = parts[index + 2] if len(parts) > index + 2 else None
    return resource, resource_id


async def run_order_maintenance_loop() -> None:
    while True:
        try:
            async with AsyncSessionFactory() as session:
                await CompleteOrderUseCase(session=session).expire_pending_orders(
                    online_timeout_minutes=settings.order_pending_online_timeout_minutes,
                    cod_timeout_hours=settings.order_pending_cod_timeout_hours,
                )
        except Exception:
            pass
        await asyncio.sleep(max(60, int(settings.order_maintenance_interval_seconds)))


@app.middleware("http")
async def admin_audit_middleware(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/admin/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        resource, resource_id = resource_from_path(request.url.path)
        actor_id = audit_actor_id(request)
        headers = {
            key: ("***" if key.lower() in SENSITIVE_AUDIT_KEYS else value)
            for key, value in request.headers.items()
            if key.lower() in {"user-agent", "content-type", "origin"}
        }
        metadata = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "resource": resource,
            "resource_id": resource_id,
            "headers": headers,
        }
        async with AsyncSessionFactory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO security_audit_logs
                        (user_id, event_type, ip_address, user_agent, metadata)
                    VALUES
                        (:user_id, :event_type, :ip_address, :user_agent, CAST(:metadata AS jsonb))
                    """
                ),
                {
                    "user_id": actor_id,
                    "event_type": f"admin_{request.method.lower()}",
                    "ip_address": audit_request_ip(request),
                    "user_agent": request.headers.get("user-agent"),
                    "metadata": json.dumps(metadata),
                },
            )
            await session.commit()
    return response


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(auth_email_router, prefix="/api/v1")
app.include_router(ai_assistant_router, prefix="/api/v1")
app.include_router(loyalty_router, prefix="/api/v1")
app.include_router(commerce_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(content_router, prefix="/api/v1")
app.include_router(storefront_router, prefix="/api/v1")
