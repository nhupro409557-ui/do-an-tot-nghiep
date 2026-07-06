from uuid import uuid4

import pytest


@pytest.mark.contract
async def test_p0_security_boundaries_reject_anonymous_spoofing(api_client):
    spoofed_user_id = str(uuid4())
    product_id = str(uuid4())
    order_payload = {
        "user_id": spoofed_user_id,
        "items": [
            {
                "product_id": product_id,
                "product_name": "Sản phẩm kiểm thử bảo mật",
                "quantity": 1,
                "unit_price": 100000,
            }
        ],
        "shipping": {
            "recipient_name": "Khách kiểm thử",
            "recipient_phone": "0900000000",
            "recipient_email": "security@example.com",
            "shipping_address": "123 Đường kiểm thử bảo mật, Thành phố Hồ Chí Minh",
        },
        "payment_method": "COD",
        "idempotency_key": f"security-order-{uuid4().hex}",
    }

    spoofed_order = await api_client.post("/api/orders", json=order_payload)
    assert spoofed_order.status_code == 401, spoofed_order.text

    offline_order = await api_client.post(
        "/api/orders",
        json={
            **order_payload,
            "user_id": None,
            "is_offline": True,
            "idempotency_key": f"security-pos-{uuid4().hex}",
        },
    )
    assert offline_order.status_code == 401, offline_order.text

    raw_user_header = await api_client.get(
        "/api/auth/me",
        headers={"X-User-Id": spoofed_user_id},
    )
    assert raw_user_header.status_code == 401, raw_user_header.text

    public_product_create = await api_client.post(
        "/api/catalog/products",
        json={"name": "Sản phẩm không được tạo public", "price": 1000},
    )
    assert public_product_create.status_code in {401, 403}, public_product_create.text

    public_mail_relay = await api_client.post(
        "/api/auth/send-verification-email",
        json={
            "email": "security@example.com",
            "name": "Security",
            "code": "123456",
            "link": "https://example.com",
            "purpose": "registration",
        },
    )
    assert public_mail_relay.status_code == 410, public_mail_relay.text


@pytest.mark.contract
async def test_google_login_requires_google_token(api_client):
    response = await api_client.post("/api/auth/google", json={"email": "attacker@example.com", "name": "Attacker"})
    assert response.status_code == 400, response.text


@pytest.mark.contract
async def test_cors_does_not_allow_untrusted_origin(api_client):
    response = await api_client.get("/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200, response.text
    assert response.headers.get("access-control-allow-origin") != "*"
    assert response.headers.get("access-control-allow-origin") != "https://evil.example"
