from uuid import uuid4

import pytest
from sqlalchemy import text


def _order_payload(customer_user, *, idempotency_key: str) -> dict:
    return {
        "user_id": customer_user["id"],
        "items": [
            {
                "product_name": "Sản phẩm kiểm thử đơn hàng admin",
                "quantity": 1,
                "unit_price": 990000,
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


@pytest.mark.workflow
async def test_admin_permissions_reject_anonymous_and_customer_for_admin_mutations(
    api_client,
    customer_headers,
    customer_user,
):
    brand_payload = {
        "name": "Thương hiệu không được tạo bởi khách",
        "code": f"NOAUTH-{uuid4().hex[:8].upper()}",
        "status": "ACTIVE",
    }

    anonymous_brand = await api_client.post("/api/admin/brands", json=brand_payload)
    assert anonymous_brand.status_code in {401, 403}, anonymous_brand.text

    customer_brand = await api_client.post(
        "/api/admin/brands",
        headers=customer_headers,
        json=brand_payload,
    )
    assert customer_brand.status_code == 403, customer_brand.text

    idempotency_key = f"admin-order-permission-{uuid4().hex}"
    created = await api_client.post(
        "/api/orders",
        headers={"Idempotency-Key": idempotency_key},
        json=_order_payload(customer_user, idempotency_key=idempotency_key),
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["order_id"]

    anonymous_order_update = await api_client.patch(
        f"/api/orders/{order_id}/admin",
        json={"status": "CONFIRMED"},
    )
    assert anonymous_order_update.status_code in {401, 403}, anonymous_order_update.text

    customer_order_update = await api_client.patch(
        f"/api/orders/{order_id}/admin",
        headers=customer_headers,
        json={"status": "CONFIRMED"},
    )
    assert customer_order_update.status_code == 403, customer_order_update.text


@pytest.mark.workflow
async def test_admin_can_update_order_status_and_internal_note(
    api_client,
    db_session,
    admin_headers,
    customer_headers,
    customer_user,
):
    idempotency_key = f"admin-order-lifecycle-{uuid4().hex}"
    created = await api_client.post(
        "/api/orders",
        headers={"Idempotency-Key": idempotency_key},
        json=_order_payload(customer_user, idempotency_key=idempotency_key),
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["order_id"]

    forbidden = await api_client.patch(
        f"/api/orders/{order_id}/admin",
        headers=customer_headers,
        json={"status": "CONFIRMED", "internal_note": "Khách không được sửa đơn"},
    )
    assert forbidden.status_code == 403, forbidden.text

    changed = await api_client.patch(
        f"/api/orders/{order_id}/admin",
        headers=admin_headers,
        json={
            "assigned_staff_name": "Nhân viên kiểm thử",
            "internal_note": "Admin đã xác nhận đơn kiểm thử",
            "changed_by": "Admin kiểm thử",
        },
    )
    assert changed.status_code == 204, changed.text

    row = (
        await db_session.execute(
            text(
                """
                SELECT status, assigned_staff_name, internal_note
                FROM orders
                WHERE id = :order_id
                """
            ),
            {"order_id": order_id},
        )
    ).mappings().one()
    assert row["status"] == "PENDING"
    assert row["assigned_staff_name"] == "Nhân viên kiểm thử"
    assert row["internal_note"] == "Admin đã xác nhận đơn kiểm thử"

    invalid_transition = await api_client.patch(
        f"/api/orders/{order_id}/admin",
        headers=admin_headers,
        json={"status": "CONFIRMED"},
    )
    assert invalid_transition.status_code == 409, invalid_transition.text
