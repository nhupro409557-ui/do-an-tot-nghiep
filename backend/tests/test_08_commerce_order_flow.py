from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_checkout_api_creates_order_and_persists_items(
    api_client,
    db_session,
    customer_headers,
    customer_user,
):
    product_id = uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status
            )
            VALUES (
                :product_id, :sku, 'Sản phẩm đặt hàng kiểm thử', :slug,
                'ACCESSORY', 'Hãng kiểm thử', 750000, 750000,
                10, 'ACTIVE'
            )
            """
        ),
        {
            "product_id": product_id,
            "sku": f"TEST-ORDER-{uuid4().hex[:8].upper()}",
            "slug": f"san-pham-dat-hang-{uuid4().hex[:8]}",
        },
    )
    await db_session.commit()

    idempotency_key = f"test-order-{uuid4().hex}"
    payload = {
        "user_id": customer_user["id"],
        "items": [
            {
                "product_id": str(product_id),
                "product_name": "Sản phẩm đặt hàng kiểm thử",
                "quantity": 2,
                "unit_price": 750000,
            }
        ],
        "shipping": {
            "recipient_name": "Khách hàng kiểm thử",
            "recipient_phone": "0900000003",
            "recipient_email": customer_user["email"],
            "shipping_address": "123 Đường kiểm thử, Thành phố Hồ Chí Minh",
        },
        "payment_method": "COD",
        "idempotency_key": idempotency_key,
    }

    created = await api_client.post(
        "/api/orders",
        headers={**customer_headers, "Idempotency-Key": idempotency_key},
        json=payload,
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["order_id"]

    row = (
        await db_session.execute(
            text(
                """
                SELECT status, total_amount, recipient_email
                FROM orders
                WHERE id = :order_id
                """
            ),
            {"order_id": order_id},
        )
    ).mappings().one()
    item_count = await db_session.scalar(
        text("SELECT COUNT(*) FROM order_items WHERE order_id = :order_id"),
        {"order_id": order_id},
    )
    assert row["status"] == "PENDING"
    assert float(row["total_amount"]) >= 1_500_000
    assert row["recipient_email"] == customer_user["email"]
    assert item_count == 1

    detail = await api_client.get(f"/api/orders/{order_id}", headers=customer_headers)
    assert detail.status_code == 200, detail.text
    assert "Sản phẩm đặt hàng kiểm thử" in detail.text
    detail_json = detail.json()
    assert detail_json["items"][0]["warrantyMonthsSnapshot"] == 12

    order_list = await api_client.get("/api/me/orders", headers=customer_headers)
    assert order_list.status_code == 200, order_list.text
    listed_order = next(order for order in order_list.json() if order["id"] == order_id)
    assert listed_order["items"][0]["warrantyMonthsSnapshot"] == 12

    repeated = await api_client.post(
        "/api/orders",
        headers={**customer_headers, "Idempotency-Key": idempotency_key},
        json=payload,
    )
    assert repeated.status_code == 201, repeated.text
    assert repeated.json()["order_id"] == order_id


@pytest.mark.workflow
async def test_checkout_consumes_limited_flash_sale_quota_and_releases_on_cancel(
    api_client,
    db_session,
    admin_headers,
    customer_headers,
    customer_user,
):
    product_id = uuid4()
    sale_id = uuid4()
    starts_at = datetime.now(UTC) - timedelta(minutes=5)
    ends_at = datetime.now(UTC) + timedelta(hours=2)
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status
            )
            VALUES (
                :product_id, :sku, 'Sản phẩm flash sale giới hạn', :slug,
                'ACCESSORY', 'Hãng kiểm thử', 1000000, 1000000,
                5, 'ACTIVE'
            )
            """
        ),
        {
            "product_id": product_id,
            "sku": f"TEST-FS-QUOTA-{uuid4().hex[:8].upper()}",
            "slug": f"san-pham-flash-sale-gioi-han-{uuid4().hex[:8]}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO flash_sales (
                id, product_id, discount_type, discount_value, starts_at,
                ends_at, status, quantity_limit
            )
            VALUES (
                :sale_id, :product_id, 'PERCENT', 50, :starts_at,
                :ends_at, 'ACTIVE', 2
            )
            """
        ),
        {
            "sale_id": sale_id,
            "product_id": product_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
    )
    await db_session.commit()

    listed = await api_client.get("/api/catalog/products?flash_sale=true&limit=100")
    assert listed.status_code == 200, listed.text
    listed_product = next(item for item in listed.json() if item["id"] == str(product_id))
    assert listed_product["flashSale"]["salePrice"] == 500000
    assert listed_product["flashSale"]["remainingQuantity"] == 2

    payload = {
        "user_id": customer_user["id"],
        "items": [
            {
                "product_id": str(product_id),
                "product_name": "Sản phẩm flash sale giới hạn",
                "quantity": 2,
                "unit_price": 500000,
            }
        ],
        "shipping": {
            "recipient_name": "Khách hàng kiểm thử",
            "recipient_phone": "0900000003",
            "recipient_email": customer_user["email"],
            "shipping_address": "123 Đường kiểm thử, Thành phố Hồ Chí Minh",
        },
        "payment_method": "COD",
        "idempotency_key": f"test-flash-sale-quota-{uuid4().hex}",
    }
    created = await api_client.post("/api/orders", headers=customer_headers, json=payload)
    assert created.status_code == 201, created.text
    order_id = created.json()["order_id"]

    sale_row = (
        await db_session.execute(
            text(
                """
                SELECT status, sold_quantity, quota_exhausted_at
                FROM flash_sales
                WHERE id = :sale_id
                """
            ),
            {"sale_id": sale_id},
        )
    ).mappings().one()
    assert sale_row["status"] == "INACTIVE"
    assert sale_row["sold_quantity"] == 2
    assert sale_row["quota_exhausted_at"] is not None

    item_row = (
        await db_session.execute(
            text(
                """
                SELECT flash_sale_id, flash_sale_quantity, flash_sale_released_at
                FROM order_items
                WHERE order_id = :order_id
                """
            ),
            {"order_id": order_id},
        )
    ).mappings().one()
    assert item_row["flash_sale_id"] == sale_id
    assert item_row["flash_sale_quantity"] == 2
    assert item_row["flash_sale_released_at"] is None

    after_exhausted = await api_client.get("/api/catalog/products?flash_sale=true&limit=100")
    assert after_exhausted.status_code == 200, after_exhausted.text
    assert str(product_id) not in {item["id"] for item in after_exhausted.json()}

    rejected = await api_client.post(
        "/api/orders",
        headers=customer_headers,
        json={
            **payload,
            "idempotency_key": f"test-flash-sale-quota-reject-{uuid4().hex}",
            "items": [{**payload["items"][0], "quantity": 1}],
        },
    )
    assert rejected.status_code == 409, rejected.text

    cancelled = await api_client.patch(
        f"/api/orders/{order_id}/admin",
        headers=admin_headers,
        json={
            "status": "CANCELLED",
            "cancellation_reason": "Khách yêu cầu hủy đơn kiểm thử.",
            "changed_by": "pytest",
        },
    )
    assert cancelled.status_code == 204, cancelled.text

    released_sale = (
        await db_session.execute(
            text(
                """
                SELECT status, sold_quantity, quota_exhausted_at
                FROM flash_sales
                WHERE id = :sale_id
                """
            ),
            {"sale_id": sale_id},
        )
    ).mappings().one()
    assert released_sale["status"] == "ACTIVE"
    assert released_sale["sold_quantity"] == 0
    assert released_sale["quota_exhausted_at"] is None

    released_item_at = await db_session.scalar(
        text("SELECT flash_sale_released_at FROM order_items WHERE order_id = :order_id"),
        {"order_id": order_id},
    )
    assert released_item_at is not None


@pytest.mark.workflow
async def test_flash_sale_quota_release_does_not_reactivate_when_overlap_exists(
    api_client,
    db_session,
    admin_headers,
    customer_headers,
    customer_user,
):
    product_id = uuid4()
    old_sale_id = uuid4()
    new_sale_id = uuid4()
    starts_at = datetime.now(UTC) - timedelta(minutes=5)
    ends_at = datetime.now(UTC) + timedelta(hours=2)
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status
            )
            VALUES (
                :product_id, :sku, 'Sản phẩm flash sale overlap', :slug,
                'ACCESSORY', 'Hãng kiểm thử', 1000000, 1000000,
                3, 'ACTIVE'
            )
            """
        ),
        {
            "product_id": product_id,
            "sku": f"TEST-FS-OVERLAP-{uuid4().hex[:8].upper()}",
            "slug": f"san-pham-flash-sale-overlap-{uuid4().hex[:8]}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO flash_sales (
                id, product_id, discount_type, discount_value, starts_at,
                ends_at, status, quantity_limit
            )
            VALUES (
                :sale_id, :product_id, 'PERCENT', 50, :starts_at,
                :ends_at, 'ACTIVE', 1
            )
            """
        ),
        {
            "sale_id": old_sale_id,
            "product_id": product_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
    )
    await db_session.commit()

    created = await api_client.post(
        "/api/orders",
        headers=customer_headers,
        json={
            "user_id": customer_user["id"],
            "items": [
                {
                    "product_id": str(product_id),
                    "product_name": "Sản phẩm flash sale overlap",
                    "quantity": 1,
                    "unit_price": 500000,
                }
            ],
            "shipping": {
                "recipient_name": "Khách hàng kiểm thử",
                "recipient_phone": "0900000003",
                "recipient_email": customer_user["email"],
                "shipping_address": "123 Đường kiểm thử, Thành phố Hồ Chí Minh",
            },
            "payment_method": "COD",
            "idempotency_key": f"test-flash-sale-overlap-{uuid4().hex}",
        },
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["order_id"]

    await db_session.execute(
        text(
            """
            INSERT INTO flash_sales (
                id, product_id, discount_type, discount_value, starts_at,
                ends_at, status, quantity_limit
            )
            VALUES (
                :sale_id, :product_id, 'PERCENT', 20, :starts_at,
                :ends_at, 'ACTIVE', NULL
            )
            """
        ),
        {
            "sale_id": new_sale_id,
            "product_id": product_id,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
    )
    await db_session.commit()

    cancelled = await api_client.patch(
        f"/api/orders/{order_id}/admin",
        headers=admin_headers,
        json={
            "status": "CANCELLED",
            "cancellation_reason": "Khách yêu cầu hủy đơn kiểm thử overlap.",
            "changed_by": "pytest",
        },
    )
    assert cancelled.status_code == 204, cancelled.text

    rows = (
        await db_session.execute(
            text(
                """
                SELECT id, status, sold_quantity
                FROM flash_sales
                WHERE id IN (:old_sale_id, :new_sale_id)
                """
            ),
            {"old_sale_id": old_sale_id, "new_sale_id": new_sale_id},
        )
    ).mappings().all()
    statuses = {row["id"]: row for row in rows}
    assert statuses[old_sale_id]["status"] == "INACTIVE"
    assert statuses[old_sale_id]["sold_quantity"] == 0
    assert statuses[new_sale_id]["status"] == "ACTIVE"


@pytest.mark.workflow
async def test_checkout_rejects_order_item_without_sellable_target(
    api_client,
    customer_headers,
    customer_user,
):
    payload = {
        "user_id": customer_user["id"],
        "items": [
            {
                "product_name": "Dòng hàng thiếu mã",
                "quantity": 1,
                "unit_price": 100000,
            }
        ],
        "shipping": {
            "recipient_name": "Khách hàng kiểm thử",
            "recipient_phone": "0900000003",
            "recipient_email": customer_user["email"],
            "shipping_address": "123 Đường kiểm thử, Thành phố Hồ Chí Minh",
        },
        "payment_method": "COD",
        "idempotency_key": f"test-order-invalid-{uuid4().hex}",
    }

    response = await api_client.post("/api/orders", headers=customer_headers, json=payload)
    assert response.status_code == 422, response.text


@pytest.mark.workflow
async def test_expired_online_payment_marks_order_failed_and_releases_reservation(
    api_client,
    db_session,
    admin_headers,
    customer_user,
):
    product_id = uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status
            )
            VALUES (
                :product_id, :sku, 'Sản phẩm thanh toán hết hạn', :slug,
                'ACCESSORY', 'Hãng kiểm thử', 450000, 450000,
                3, 'ACTIVE'
            )
            """
        ),
        {
            "product_id": product_id,
            "sku": f"TEST-PAY-EXP-{uuid4().hex[:8].upper()}",
            "slug": f"san-pham-payment-expire-{uuid4().hex[:8]}",
        },
    )
    await db_session.commit()

    order_id = uuid4()
    order_item_id = uuid4()
    payment_id = uuid4()
    location_id = await db_session.scalar(text("SELECT id FROM inventory_locations WHERE code = 'MAIN' LIMIT 1"))
    assert location_id is not None
    await db_session.execute(
        text(
            """
            INSERT INTO orders (
                id, user_id, order_code, status, payment_method, payment_status,
                subtotal_amount, discount_amount, shipping_fee, total_amount,
                recipient_name, recipient_phone, recipient_email, shipping_address
            )
            VALUES (
                :order_id, :user_id, :order_code, 'PENDING', 'SEPAY', 'PENDING',
                450000, 0, 0, 450000,
                'Khách hàng kiểm thử', '0900000003', :email,
                '123 Đường kiểm thử, Thành phố Hồ Chí Minh'
            )
            """
        ),
        {
            "order_id": order_id,
            "user_id": customer_user["id"],
            "order_code": f"TESTPAY{uuid4().hex[:8].upper()}",
            "email": customer_user["email"],
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO order_items (
                id, order_id, product_id, product_name, quantity, unit_price, total_price
            )
            VALUES (
                :order_item_id, :order_id, :product_id,
                'Sản phẩm thanh toán hết hạn', 1, 450000, 450000
            )
            """
        ),
        {"order_item_id": order_item_id, "order_id": order_id, "product_id": product_id},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_reservations (
                id, product_id, location_id, order_id, reservation_code,
                reserved_quantity, status, expires_at
            )
            VALUES (
                gen_random_uuid(), :product_id, :location_id, :order_id, :reservation_code,
                1, 'ACTIVE', NOW() + INTERVAL '1 hour'
            )
            """
        ),
        {
            "product_id": product_id,
            "location_id": location_id,
            "order_id": order_id,
            "reservation_code": f"ORDER-EXPIRE-{uuid4().hex[:10]}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO payment_transactions (
                id, order_id, provider, amount, status, transaction_ref,
                attempt_number, expires_at, raw_response
            )
            VALUES (
                :payment_id, :order_id, 'SEPAY', 450000, 'PENDING', :transaction_ref,
                1, NOW() - INTERVAL '1 minute', '{}'::jsonb
            )
            """
        ),
        {
            "payment_id": payment_id,
            "order_id": order_id,
            "transaction_ref": f"TEST-SEPAY-{uuid4().hex[:8]}",
        },
    )
    await db_session.commit()

    expired = await api_client.post("/api/orders/maintenance/expire-pending", headers=admin_headers)
    assert expired.status_code == 200, expired.text
    assert expired.json()["expiredPayments"] >= 1

    row = (
        await db_session.execute(
            text(
                """
                SELECT o.status AS order_status, o.payment_status, r.status AS reservation_status
                FROM orders o
                JOIN inventory_reservations r ON r.order_id = o.id
                WHERE o.id = :order_id
                """
            ),
            {"order_id": order_id},
        )
    ).mappings().one()
    assert row["order_status"] == "PAYMENT_FAILED"
    assert row["payment_status"] == "FAILED"
    assert row["reservation_status"] == "EXPIRED"


@pytest.mark.workflow
async def test_checkout_rejects_client_price_tampering(
    api_client,
    db_session,
    customer_headers,
    customer_user,
):
    product_id = uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status
            )
            VALUES (
                :product_id, :sku, 'Sản phẩm chống sửa giá', :slug,
                'ACCESSORY', 'Hãng kiểm thử', 900000, 900000,
                2, 'ACTIVE'
            )
            """
        ),
        {
            "product_id": product_id,
            "sku": f"TEST-PRICE-{uuid4().hex[:8].upper()}",
            "slug": f"san-pham-chong-sua-gia-{uuid4().hex[:8]}",
        },
    )
    await db_session.commit()

    response = await api_client.post(
        "/api/orders",
        headers=customer_headers,
        json={
            "user_id": customer_user["id"],
            "items": [
                {
                    "product_id": str(product_id),
                    "product_name": "Sản phẩm chống sửa giá",
                    "quantity": 1,
                    "unit_price": 1,
                }
            ],
            "shipping": {
                "recipient_name": "Khách hàng kiểm thử",
                "recipient_phone": "0900000003",
                "recipient_email": customer_user["email"],
                "shipping_address": "123 Đường kiểm thử, Thành phố Hồ Chí Minh",
            },
            "payment_method": "COD",
            "idempotency_key": f"test-price-tamper-{uuid4().hex}",
        },
    )
    assert response.status_code == 409, response.text
