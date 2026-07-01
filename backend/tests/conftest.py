from __future__ import annotations

import asyncio
import atexit
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
TEST_DATABASE_PREFIX = "project_test_"
LOCAL_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1"}

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_admin_url: str | None = None
_test_database_name: str | None = None
_cleanup_done = False


def _read_env_value(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=\s*(.*?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip().strip("'\"")
    return None


def _normalize_asyncpg_url(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _replace_database(database_url: str, database_name: str) -> str:
    parsed = urlsplit(_normalize_asyncpg_url(database_url))
    return urlunsplit((parsed.scheme, parsed.netloc, f"/{database_name}", "", ""))


def _load_admin_url() -> str:
    explicit = os.getenv("TEST_DATABASE_ADMIN_URL")
    if explicit:
        return _normalize_asyncpg_url(explicit)

    configured = os.getenv("DATABASE_URL") or _read_env_value(BACKEND_DIR / ".env", "DATABASE_URL")
    if not configured:
        raise pytest.UsageError(
            "Thiếu TEST_DATABASE_ADMIN_URL. Hãy trỏ biến này tới PostgreSQL local; "
            "runner chỉ dùng kết nối đó để tạo và xóa database test riêng."
        )
    return _normalize_asyncpg_url(configured)


def _assert_safe_admin_server(admin_url: str) -> None:
    parsed = urlsplit(admin_url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise pytest.UsageError("TEST_DATABASE_ADMIN_URL phải là URL PostgreSQL.")
    if (
        parsed.hostname not in LOCAL_DATABASE_HOSTS
        and os.getenv("ALLOW_REMOTE_TEST_DATABASE") != "1"
    ):
        raise pytest.UsageError(
            "Đã chặn tạo database test trên máy chủ từ xa. Dùng PostgreSQL local hoặc "
            "máy chủ test chuyên biệt với ALLOW_REMOTE_TEST_DATABASE=1."
        )


def _quoted_identifier(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9_]+", value):
        raise pytest.UsageError("Tên database test không hợp lệ.")
    return f'"{value}"'


async def _create_test_database(admin_url: str, database_name: str) -> None:
    maintenance_url = _replace_database(admin_url, "postgres")
    connection = await asyncpg.connect(maintenance_url)
    try:
        await connection.execute(f"CREATE DATABASE {_quoted_identifier(database_name)}")
    finally:
        await connection.close()


async def _apply_migrations(test_url: str) -> None:
    from scripts.run_migrations import discover_sql_files, run_migration_file

    migrations_dir = BACKEND_DIR / "migrations"
    connection = await asyncpg.connect(test_url)
    try:
        filenames = discover_sql_files(str(migrations_dir))
        await run_migration_file(connection, str(migrations_dir / filenames[0]))
        # Baseline có dữ liệu trình diễn cũ. Test tích hợp phải tự tạo dữ liệu,
        # đồng thời không để migration chuyển kệ phụ thuộc snapshot dữ liệu cũ.
        await connection.execute("TRUNCATE TABLE products CASCADE")
        for filename in filenames[1:]:
            await run_migration_file(connection, str(migrations_dir / filename))
    finally:
        await connection.close()


async def _drop_test_database(admin_url: str, database_name: str) -> None:
    maintenance_url = _replace_database(admin_url, "postgres")
    connection = await asyncpg.connect(maintenance_url)
    try:
        await connection.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = $1 AND pid <> pg_backend_pid()
            """,
            database_name,
        )
        await connection.execute(f"DROP DATABASE IF EXISTS {_quoted_identifier(database_name)}")
    finally:
        await connection.close()


def _cleanup_test_database() -> None:
    global _cleanup_done
    if _cleanup_done or not _admin_url or not _test_database_name:
        return
    _cleanup_done = True
    try:
        asyncio.run(_drop_test_database(_admin_url, _test_database_name))
    except Exception as exc:
        print(f"Không thể tự động xóa database test {_test_database_name}: {exc}")


def pytest_sessionstart(session: pytest.Session) -> None:
    global _admin_url, _test_database_name
    _admin_url = _load_admin_url()
    _assert_safe_admin_server(_admin_url)
    _test_database_name = f"{TEST_DATABASE_PREFIX}{os.getpid()}_{uuid4().hex[:8]}"
    test_url = _replace_database(_admin_url, _test_database_name)

    asyncio.run(_create_test_database(_admin_url, _test_database_name))
    os.environ["DATABASE_URL"] = test_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    os.environ["TEST_DATABASE_NAME"] = _test_database_name
    os.environ["ORDER_MAINTENANCE_ENABLED"] = "false"
    os.environ["SMTP_USERNAME"] = ""
    os.environ["SMTP_PASSWORD"] = ""
    os.environ["MOMO_SECRET_KEY"] = ""
    os.environ["ZALOPAY_KEY1"] = ""
    os.environ["ZALOPAY_KEY2"] = ""
    os.environ["SEPAY_SECRET_KEY"] = ""
    try:
        asyncio.run(_apply_migrations(test_url))
    except Exception:
        asyncio.run(_drop_test_database(_admin_url, _test_database_name))
        raise

    atexit.register(_cleanup_test_database)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    from app.infrastructure.database.session import engine

    asyncio.run(engine.dispose())
    _cleanup_test_database()


@pytest.fixture
async def db_session():
    from app.infrastructure.database.session import AsyncSessionFactory
    from app.testing.database_guard import assert_isolated_test_database_url
    from app.config import settings

    assert_isolated_test_database_url(settings.database_url)
    async with AsyncSessionFactory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def api_client():
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"user-agent": "project-integration-tests"},
    ) as client:
        yield client


async def _create_user(db_session, role_code: str, email_prefix: str) -> dict[str, str]:
    from app.api.routers.auth_utils import make_token, pwd_context

    user_id = uuid4()
    email = f"{email_prefix}-{uuid4().hex[:8]}@example.com"
    password = "MatKhauTest123!"
    await db_session.execute(
        text(
            """
            INSERT INTO users (id, role_id, email, password_hash, full_name, status)
            SELECT :user_id, id, :email, :password_hash, :full_name, 'ACTIVE'
            FROM roles
            WHERE code = :role_code
            """
        ),
        {
            "user_id": user_id,
            "email": email,
            "password_hash": pwd_context.hash(password),
            "full_name": f"Người dùng kiểm thử {role_code}",
            "role_code": role_code,
        },
    )
    await db_session.commit()
    return {
        "id": str(user_id),
        "email": email,
        "password": password,
        "token": make_token(user_id),
    }


@pytest.fixture
async def customer_user(db_session):
    return await _create_user(db_session, "CUSTOMER", "customer")


@pytest.fixture
async def admin_user(db_session):
    return await _create_user(db_session, "SUPER_ADMIN", "admin")


@pytest.fixture
async def approver_user(db_session):
    return await _create_user(db_session, "SUPER_ADMIN", "approver")


@pytest.fixture
def customer_headers(customer_user):
    return {"Authorization": f"Bearer {customer_user['token']}"}


@pytest.fixture
def admin_headers(admin_user):
    return {"Authorization": f"Bearer {admin_user['token']}"}


@pytest.fixture
def approver_headers(approver_user):
    return {"Authorization": f"Bearer {approver_user['token']}"}
