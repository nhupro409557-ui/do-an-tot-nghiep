from uuid import uuid4

import pytest


@pytest.mark.workflow
async def test_verification_flows_do_not_expose_email_tokens(api_client, monkeypatch, customer_user):
    from app.api.routers import auth_verification

    monkeypatch.setattr(auth_verification, "send_auth_email", lambda *args, **kwargs: None)

    register = await api_client.post(
        "/api/auth/register/start",
        json={
            "email": f"register-{uuid4().hex[:8]}@example.com",
            "password": "MatKhauTest123!",
            "displayName": "Khách đăng ký kiểm thử",
        },
    )
    assert register.status_code == 200, register.text
    assert "verificationToken" not in register.json()

    forgot = await api_client.post(
        "/api/auth/forgot-password",
        json={"email": customer_user["email"]},
    )
    assert forgot.status_code == 200, forgot.text
    assert "verificationToken" not in forgot.json()
