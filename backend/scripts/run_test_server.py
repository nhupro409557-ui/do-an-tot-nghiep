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
TEST_SUPER_ADMIN_EMAIL = "e2e-super-admin@example.com"
TEST_SUPER_ADMIN_PASSWORD = "MatKhauSuperAdminE2E123!"
TEST_PAYABLE_ADMIN_EMAIL = "e2e-payable-admin@example.com"
TEST_PAYABLE_ADMIN_PASSWORD = "MatKhauCongNoE2E123!"
TEST_PRODUCT_NAME = "Sản phẩm kiểm thử luồng dữ liệu E2E"
TEST_PAYABLE_REFERENCE = "NK-E2E-CONGNO-001"
TEST_INVENTORY_RECEIPT_REFERENCE = "NK-E2E-EXCEL-001"


async def seed_e2e_data(test_url: str) -> None:
    from app.api.routers.auth_utils import pwd_context

    connection = await asyncpg.connect(test_url)
    try:
        customer_role_id = await connection.fetchval(
            "SELECT id FROM roles WHERE code = 'CUSTOMER'"
        )
        super_admin_role_id = await connection.fetchval(
            "SELECT id FROM roles WHERE code = 'SUPER_ADMIN'"
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
        inventory_location = await connection.fetchrow(
            """
            SELECT id, code, name
            FROM inventory_locations
            WHERE status = 'ACTIVE' AND purpose IN ('STORAGE', 'VIRTUAL')
            ORDER BY CASE WHEN code = 'MAIN' THEN 0 ELSE 1 END, sort_order, code
            LIMIT 1
            """
        )
        if not inventory_location:
            raise RuntimeError("Không có kệ đang hoạt động để seed phiếu nhập E2E.")
        user_id = uuid4()
        admin_user_id = uuid4()
        super_admin_user_id = uuid4()
        payable_admin_user_id = uuid4()
        product_id = uuid4()
        inventory_receipt_document_id = uuid4()
        inventory_receipt_line_id = uuid4()
        supplier_id = uuid4()
        payable_document_id = uuid4()
        payable_id = uuid4()
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
            INSERT INTO users (
                id, role_id, email, password_hash, full_name, status
            )
            VALUES ($1, $2, $3, $4, $5, 'ACTIVE')
            """,
            super_admin_user_id,
            super_admin_role_id,
            TEST_SUPER_ADMIN_EMAIL,
            pwd_context.hash(TEST_SUPER_ADMIN_PASSWORD),
            "Super Admin E2E",
        )
        await connection.execute(
            """
            INSERT INTO users (
                id, role_id, email, password_hash, full_name, status
            )
            VALUES ($1, $2, $3, $4, $5, 'ACTIVE')
            """,
            payable_admin_user_id,
            staff_role_id,
            TEST_PAYABLE_ADMIN_EMAIL,
            pwd_context.hash(TEST_PAYABLE_ADMIN_PASSWORD),
            "Kế toán công nợ E2E",
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
                "inventory:adjust",
                "content:read",
                "payment_method:read",
            ],
        )
        await connection.execute(
            """
            INSERT INTO user_permissions (user_id, permission_id)
            SELECT $1, id
            FROM permissions
            WHERE code = ANY($2::text[])
            ON CONFLICT DO NOTHING
            """,
            payable_admin_user_id,
            [
                "overview:read",
                "inventory:read",
                "inventory:adjust",
                "supplier:read",
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
        await connection.execute(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status, target_location_id,
                supplier_name, reference_code, reason, note, metadata, created_by
            )
            VALUES (
                $1, $2, 'INBOUND', 'PROCESSING_IMEI', $3,
                'Nhà cung cấp E2E Excel', $2, 'NK_MUA',
                'Phiếu nhập kiểm thử import Excel', $4::jsonb, $5
            )
            """,
            inventory_receipt_document_id,
            TEST_INVENTORY_RECEIPT_REFERENCE,
            inventory_location["id"],
            json.dumps(
                {
                    "qualityStatus": "PENDING",
                    "quarantine": False,
                },
                ensure_ascii=False,
            ),
            admin_user_id,
        )
        await connection.execute(
            """
            INSERT INTO inventory_document_lines (
                id, document_id, product_id, variant_id, location_id,
                requested_quantity, expected_quantity, unit_cost, note, metadata
            )
            VALUES (
                $1, $2, $3, NULL, $4,
                2, 2, 450000, 'Dòng kiểm thử import IMEI/serial từ Excel', $5::jsonb
            )
            """,
            inventory_receipt_line_id,
            inventory_receipt_document_id,
            product_id,
            inventory_location["id"],
            json.dumps(
                {
                    "imeis": [],
                    "tracksImei": True,
                    "serialNumbers": [],
                    "tracksSerialNumber": True,
                    "plannedQuantity": 2,
                    "receivedQuantity": 0,
                    "storageLocationCode": inventory_location["code"],
                    "storageLocationName": inventory_location["name"],
                },
                ensure_ascii=False,
            ),
        )
        await connection.execute(
            """
            INSERT INTO suppliers (
                id, code, name, contact_name, phone, email, address, tax_code, is_active
            )
            VALUES (
                $1, 'NCC-E2E-CONGNO', 'Nhà cung cấp E2E Công nợ',
                'Kế toán NCC', '0900000000', 'ncc-e2e-congno@example.com',
                'Kho kiểm thử E2E', 'MST-E2E-CN', TRUE
            )
            """,
            supplier_id,
        )
        await connection.execute(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status, supplier_name, reference_code,
                reason, note, metadata, created_by, approved_by, posted_by, approved_at, posted_at
            )
            VALUES (
                $1, $2, 'INBOUND', 'COMPLETED', 'Nhà cung cấp E2E Công nợ', $2,
                'NK_MUA', 'Phiếu nhập kiểm thử công nợ NCC', $3::jsonb,
                $4, $4, $4, NOW(), NOW()
            )
            """,
            payable_document_id,
            TEST_PAYABLE_REFERENCE,
            json.dumps(
                {
                    "supplierId": str(supplier_id),
                    "supplierName": "Nhà cung cấp E2E Công nợ",
                    "paymentMode": "DEBT",
                    "paymentTermDays": 15,
                    "dueDate": "2099-12-31T00:00:00Z",
                    "invoiceNumber": "HD-E2E-CN-001",
                    "paidAmount": 500000,
                },
                ensure_ascii=False,
            ),
            payable_admin_user_id,
        )
        await connection.execute(
            """
            INSERT INTO account_payables (
                id, supplier_id, supplier_name_snapshot, source_document_id,
                source_reference_code, invoice_number, invoice_date, principal_amount,
                paid_amount, remaining_amount, payment_term_days, due_date, status,
                note, created_by, updated_by
            )
            VALUES (
                $1, $2, 'Nhà cung cấp E2E Công nợ', $3, $4, 'HD-E2E-CN-001',
                NOW(), 2500000, 500000, 2000000, 15, '2099-12-31 00:00:00+00',
                'PARTIAL', 'Dữ liệu kiểm thử giao diện công nợ NCC', $5, $5
            )
            """,
            payable_id,
            supplier_id,
            payable_document_id,
            TEST_PAYABLE_REFERENCE,
            payable_admin_user_id,
        )
        await connection.execute(
            """
            INSERT INTO supplier_payments (
                payable_id, supplier_id, payment_code, amount, method,
                reference_no, note, created_by
            )
            VALUES (
                $1, $2, 'PCN-E2E-001', 500000, 'BANK_TRANSFER',
                'UNC-E2E-001', 'Thanh toán một phần khi kiểm thử UI', $3
            )
            """,
            payable_id,
            supplier_id,
            payable_admin_user_id,
        )
        await connection.execute(
            """
            INSERT INTO account_payable_events (payable_id, event_type, amount, actor_id, metadata)
            VALUES ($1, 'PAYMENT_RECORDED', 500000, $2, '{"source":"e2e_seed"}'::jsonb)
            """,
            payable_id,
            payable_admin_user_id,
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
