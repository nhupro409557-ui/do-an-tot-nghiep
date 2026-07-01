from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_checkout_api_creates_order_and_persists_items(
    api_client,
    db_session,
    customer_user,
):
    idempotency_key = f"test-order-{uuid4().hex}"
    payload = {
        "user_id": customer_user["id"],
        "items": [
            {
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
        headers={"Idempotency-Key": idempotency_key},
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

    detail = await api_client.get(f"/api/orders/{order_id}")
    assert detail.status_code == 200, detail.text
    assert "Sản phẩm đặt hàng kiểm thử" in detail.text

    repeated = await api_client.post(
        "/api/orders",
        headers={"Idempotency-Key": idempotency_key},
        json=payload,
    )
    assert repeated.status_code == 201, repeated.text
    assert repeated.json()["order_id"] == order_id
