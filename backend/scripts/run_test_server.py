from __future__ import annotations

import argparse
import asyncio
import atexit
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

import asyncpg


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from tests.conftest import (  # noqa: E402
    TEST_DATABASE_PREFIX,
    _apply_migrations,
    _assert_safe_admin_server,
    _create_test_database,
    _drop_test_database,
    _load_admin_url,
    _replace_database,
)


TEST_CUSTOMER_EMAIL = "e2e-customer@example.com"
TEST_CUSTOMER_PASSWORD = "MatKhauE2E123!"
TEST_ADMIN_EMAIL = "e2e-admin@example.com"
TEST_ADMIN_PASSWORD = "MatKhauAdminE2E123!"
TEST_PRODUCT_NAME = "Sản phẩm kiểm thử luồng dữ liệu E2E"


async def seed_e2e_data(test_url: str) -> None:
    from app.api.routers.auth_utils import pwd_context

    connection = await asyncpg.connect(test_url)
    try:
        customer_role_id = await connection.fetchval(
            "SELECT id FROM roles WHERE code = 'CUSTOMER'"
        )
        staff_role_id = await connection.fetchval(
            "SELECT id FROM roles WHERE code = 'STAFF_ADMIN'"
        )
        category_id = await connection.fetchval(
            """
            SELECT id FROM categories
            WHERE is_active = TRUE
            ORDER BY created_at
            LIMIT 1
            """
        )
        user_id = uuid4()
        admin_user_id = uuid4()
        product_id = uuid4()
        await connection.execute(
            """
            INSERT INTO users (
                id, role_id, email, password_hash, full_name, status
            )
            VALUES ($1, $2, $3, $4, $5, 'ACTIVE')
            """,
            user_id,
            customer_role_id,
            TEST_CUSTOMER_EMAIL,
            pwd_context.hash(TEST_CUSTOMER_PASSWORD),
            "Khách hàng E2E",
        )
        await connection.execute(
            """
            INSERT INTO users (
                id, role_id, email, password_hash, full_name, status
            )
            VALUES ($1, $2, $3, $4, $5, 'ACTIVE')
            """,
            admin_user_id,
            staff_role_id,
            TEST_ADMIN_EMAIL,
            pwd_context.hash(TEST_ADMIN_PASSWORD),
            "Quản trị viên E2E",
        )
        await connection.execute(
            """
            INSERT INTO user_permissions (user_id, permission_id)
            SELECT $1, id
            FROM permissions
            WHERE code = ANY($2::text[])
            ON CONFLICT DO NOTHING
            """,
            admin_user_id,
            [
                "overview:read",
                "product:read",
                "order:read",
                "customer:read",
                "customer:update",
                "inventory:read",
                "content:read",
                "payment_method:read",
            ],
        )
        await connection.execute(
            """
            INSERT INTO products (
                id, sku, name, slug, category, category_id, brand,
                description, price, stock_quantity, image_url, status
            )
            VALUES (
                $1, $2, $3, $4, 'ACCESSORY', $5, 'Hãng kiểm thử',
                'Dữ liệu được tạo riêng cho phiên Playwright.', 990000, 5,
                'https://placehold.co/600x600/png', 'ACTIVE'
            )
            """,
            product_id,
            f"TEST-E2E-{uuid4().hex[:8].upper()}",
            TEST_PRODUCT_NAME,
            f"san-pham-e2e-{uuid4().hex[:8]}",
            category_id,
        )
    finally:
        await connection.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    admin_url = _load_admin_url()
    _assert_safe_admin_server(admin_url)
    database_name = f"{TEST_DATABASE_PREFIX}e2e_{os.getpid()}_{uuid4().hex[:8]}"
    test_url = _replace_database(admin_url, database_name)
    state_file = os.getenv("TEST_DATABASE_STATE_FILE")
    cleaned = False

    async def cleanup() -> None:
        nonlocal cleaned
        if cleaned:
            return
        cleaned = True
        try:
            from app.infrastructure.database.session import engine

            await engine.dispose()
        except Exception:
            pass
        await _drop_test_database(admin_url, database_name)
        if state_file:
            Path(state_file).unlink(missing_ok=True)

    def cleanup_sync() -> None:
        if cleaned:
            return
        try:
            asyncio.run(cleanup())
        except Exception as exc:
            print(f"Không thể xóa database E2E {database_name}: {exc}")

    asyncio.run(_create_test_database(admin_url, database_name))
    if state_file:
        state_path = Path(state_file)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps({"databaseName": database_name}),
            encoding="utf-8",
        )
    os.environ["DATABASE_URL"] = test_url.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )
    os.environ["TEST_DATABASE_NAME"] = database_name
    os.environ["ORDER_MAINTENANCE_ENABLED"] = "false"
    os.environ["SMTP_USERNAME"] = ""
    os.environ["SMTP_PASSWORD"] = ""
    try:
        asyncio.run(_apply_migrations(test_url))
        asyncio.run(seed_e2e_data(test_url))
    except Exception:
        asyncio.run(cleanup())
        raise

    atexit.register(cleanup_sync)
    print(f"Database E2E cô lập: {database_name}")

    import uvicorn

    try:
        uvicorn.run("app.main:app", host=args.host, port=args.port, log_level="warning")
    finally:
        cleanup_sync()


if __name__ == "__main__":
    main()
