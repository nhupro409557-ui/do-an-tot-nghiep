import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_login_profile_update_and_database_persistence(
    api_client,
    db_session,
    customer_user,
):
    login = await api_client.post(
        "/api/auth/login",
        json={"email": customer_user["email"], "password": customer_user["password"]},
    )
    assert login.status_code == 200, login.text
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await api_client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["user"]["email"] == customer_user["email"]

    update = await api_client.patch(
        "/api/auth/me/profile",
        headers=headers,
        json={
            "data": {
                "displayName": "Khách hàng kiểm thử",
                "phone": "0900000001",
                "marketingOptIn": True,
            }
        },
    )
    assert update.status_code == 200, update.text

    row = (
        await db_session.execute(
            text(
                """
                SELECT full_name, phone, marketing_opt_in
                FROM users
                WHERE id = :user_id
                """
            ),
            {"user_id": customer_user["id"]},
        )
    ).mappings().one()
    assert row["full_name"] == "Khách hàng kiểm thử"
    assert row["phone"] == "0900000001"
    assert row["marketing_opt_in"] is True
