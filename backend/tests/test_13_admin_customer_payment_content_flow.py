from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_admin_customer_profile_tags_notes_loyalty_and_permission_guards(
    api_client,
    db_session,
    admin_headers,
    customer_headers,
    customer_user,
):
    forbidden = await api_client.get(
        "/api/admin/customers",
        headers=customer_headers,
    )
    assert forbidden.status_code == 403, forbidden.text

    listed = await api_client.get(
        "/api/admin/customers",
        headers=admin_headers,
        params={"search": customer_user["email"]},
    )
    assert listed.status_code == 200, listed.text
    assert customer_user["email"] in listed.text

    updated_profile = await api_client.patch(
        f"/api/admin/customers/{customer_user['id']}/profile",
        headers=admin_headers,
        json={
            "fullName": "Khách hàng admin cập nhật",
            "phone": "0900000099",
            "tier": "GOLD",
            "walletStatus": "ACTIVE",
        },
    )
    assert updated_profile.status_code == 200, updated_profile.text

    updated_tags = await api_client.put(
        f"/api/admin/customers/{customer_user['id']}/tags",
        headers=admin_headers,
        json={"tags": [" VIP ", "vip", "Kiểm thử"]},
    )
    assert updated_tags.status_code == 200, updated_tags.text
    assert updated_tags.json()["tags"] == ["VIP", "Kiểm thử"]

    note = await api_client.post(
        f"/api/admin/customers/{customer_user['id']}/notes",
        headers=admin_headers,
        json={"content": "Ghi chú chăm sóc khách hàng kiểm thử"},
    )
    assert note.status_code == 200, note.text

    loyalty = await api_client.post(
        f"/api/admin/customers/{customer_user['id']}/loyalty-adjustments",
        headers=admin_headers,
        json={"delta": 120, "reason": "Cộng điểm kiểm thử admin"},
    )
    assert loyalty.status_code == 200, loyalty.text
    assert loyalty.json()["balanceAfter"] == loyalty.json()["balanceBefore"] + 120

    row = (
        await db_session.execute(
            text(
                """
                SELECT full_name, phone, loyalty_tier, loyalty_wallet_status, loyalty_points_balance
                FROM users
                WHERE id = :user_id
                """
            ),
            {"user_id": customer_user["id"]},
        )
    ).mappings().one()
    assert row["full_name"] == "Khách hàng admin cập nhật"
    assert row["phone"] == "0900000099"
    assert row["loyalty_tier"] == "GOLD"
    assert row["loyalty_wallet_status"] == "ACTIVE"
    assert row["loyalty_points_balance"] == 120

    tags = [
        item[0]
        for item in (
            await db_session.execute(
                text("SELECT tag FROM customer_tags WHERE user_id = :user_id ORDER BY tag"),
                {"user_id": customer_user["id"]},
            )
        ).all()
    ]
    assert tags == ["Kiểm thử", "VIP"]

    note_count = await db_session.scalar(
        text("SELECT COUNT(*) FROM customer_notes WHERE user_id = :user_id"),
        {"user_id": customer_user["id"]},
    )
    assert note_count == 1

    invalid_loyalty = await api_client.post(
        f"/api/admin/customers/{customer_user['id']}/loyalty-adjustments",
        headers=admin_headers,
        json={"delta": 0, "reason": "Không hợp lệ"},
    )
    assert invalid_loyalty.status_code == 400, invalid_loyalty.text


@pytest.mark.workflow
async def test_admin_payment_method_toggle_affects_public_checkout_methods(
    api_client,
    db_session,
    admin_headers,
    customer_headers,
):
    forbidden = await api_client.get(
        "/api/admin/payment-methods",
        headers=customer_headers,
    )
    assert forbidden.status_code == 403, forbidden.text

    methods = await api_client.get("/api/admin/payment-methods", headers=admin_headers)
    assert methods.status_code == 200, methods.text
    cod_method = next((item for item in methods.json() if item["code"] == "COD"), None)
    assert cod_method is not None, methods.text

    disabled = await api_client.patch(
        f"/api/admin/payment-methods/{cod_method['id']}",
        headers=admin_headers,
        json={
            "is_active": False,
            "maintenance_message": "Tạm tắt COD trong kiểm thử",
        },
    )
    assert disabled.status_code == 200, disabled.text

    public_methods = await api_client.get("/api/payment-methods")
    assert public_methods.status_code == 200, public_methods.text
    public_cod = next((item for item in public_methods.json() if item["code"] == "COD"), None)
    assert public_cod is not None, public_methods.text
    assert public_cod["is_available"] is False
    assert public_cod["maintenance_message"] == "Tạm tắt COD trong kiểm thử"

    row = (
        await db_session.execute(
            text("SELECT is_active, maintenance_message FROM payment_methods WHERE id = :method_id"),
            {"method_id": cod_method["id"]},
        )
    ).mappings().one()
    assert row["is_active"] is False
    assert row["maintenance_message"] == "Tạm tắt COD trong kiểm thử"

    enabled = await api_client.patch(
        f"/api/admin/payment-methods/{cod_method['id']}",
        headers=admin_headers,
        json={
            "is_active": True,
            "maintenance_message": None,
        },
    )
    assert enabled.status_code == 200, enabled.text


def _video_payload(*, title: str, version: int | None = None) -> dict:
    payload = {
        "title": title,
        "description": "Video nội dung kiểm thử admin",
        "contentType": "VIDEO",
        "videoSource": "UPLOAD",
        "videoCategory": "PRODUCT",
        "status": "PUBLISHED",
        "videoUrl": "https://cdn.example.com/admin-video-test.mp4",
        "thumbnailUrl": "https://cdn.example.com/admin-video-test.jpg",
        "contentBody": "Nội dung mô tả video kiểm thử",
        "isActive": True,
        "sortOrder": 1,
        "comments": [
            {
                "userName": "Khách kiểm thử",
                "content": "Bình luận kiểm thử",
                "isHidden": False,
            }
        ],
    }
    if version is not None:
        payload["version"] = version
    return payload


@pytest.mark.workflow
async def test_admin_video_content_crud_and_validation(
    api_client,
    db_session,
    admin_headers,
    customer_headers,
):
    forbidden = await api_client.post(
        "/api/admin/videos",
        headers=customer_headers,
        json=_video_payload(title="Video khách không được tạo"),
    )
    assert forbidden.status_code == 403, forbidden.text

    invalid = await api_client.post(
        "/api/admin/videos",
        headers=admin_headers,
        json={**_video_payload(title="Video URL sai"), "videoUrl": "https://cdn.example.com/video.txt"},
    )
    assert invalid.status_code == 422, invalid.text

    created = await api_client.post(
        "/api/admin/videos",
        headers=admin_headers,
        json=_video_payload(title="Video kiểm thử admin"),
    )
    assert created.status_code == 201, created.text
    video_id = created.json()["id"]

    listed = await api_client.get("/api/admin/videos", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    created_item = next((item for item in listed.json() if item["id"] == video_id), None)
    assert created_item is not None, listed.text
    assert created_item["version"] == 1

    missing_version = await api_client.patch(
        f"/api/admin/videos/{video_id}",
        headers=admin_headers,
        json=_video_payload(title="Thiếu version"),
    )
    assert missing_version.status_code == 409, missing_version.text

    updated = await api_client.patch(
        f"/api/admin/videos/{video_id}",
        headers=admin_headers,
        json=_video_payload(title="Video kiểm thử admin đã cập nhật", version=created_item["version"]),
    )
    assert updated.status_code == 200, updated.text

    row = (
        await db_session.execute(
            text(
                """
                SELECT title, content_type, status, version, deleted_at
                FROM videos
                WHERE id = :video_id
                """
            ),
            {"video_id": video_id},
        )
    ).mappings().one()
    assert row["title"] == "Video kiểm thử admin đã cập nhật"
    assert row["content_type"] == "VIDEO"
    assert row["status"] == "PUBLISHED"
    assert row["version"] == 2
    assert row["deleted_at"] is None

    comment_count = await db_session.scalar(
        text("SELECT COUNT(*) FROM content_comments WHERE content_id = :video_id"),
        {"video_id": video_id},
    )
    assert comment_count == 1

    deleted = await api_client.delete(
        f"/api/admin/videos/{video_id}",
        headers=admin_headers,
    )
    assert deleted.status_code == 200, deleted.text

    deleted_at = await db_session.scalar(
        text("SELECT deleted_at FROM videos WHERE id = :video_id"),
        {"video_id": video_id},
    )
    assert deleted_at is not None
