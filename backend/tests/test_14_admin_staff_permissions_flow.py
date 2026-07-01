from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_admin_staff_account_and_extra_permissions_flow(
    api_client,
    db_session,
    admin_headers,
    customer_headers,
    admin_user,
):
    forbidden = await api_client.get(
        "/api/admin/permissions",
        headers=customer_headers,
    )
    assert forbidden.status_code == 403, forbidden.text

    permissions = await api_client.get("/api/admin/permissions", headers=admin_headers)
    assert permissions.status_code == 200, permissions.text
    permission_codes = {item["code"] for item in permissions.json()}
    assert {"customer:read", "inventory:read"}.issubset(permission_codes)

    roles = await api_client.get("/api/admin/roles", headers=admin_headers)
    assert roles.status_code == 200, roles.text
    staff_role = next((item for item in roles.json() if item["code"] == "STAFF_ADMIN"), None)
    customer_role = next((item for item in roles.json() if item["code"] == "CUSTOMER"), None)
    assert staff_role is not None, roles.text
    assert customer_role is not None, roles.text

    staff_email = f"staff-{uuid4().hex[:8]}@example.com"
    forbidden_create = await api_client.post(
        "/api/admin/staff",
        headers=customer_headers,
        json={
            "email": staff_email,
            "password": "MatKhauStaff123!",
            "fullName": "Nhân viên không được tạo",
        },
    )
    assert forbidden_create.status_code == 403, forbidden_create.text

    created = await api_client.post(
        "/api/admin/staff",
        headers=admin_headers,
        json={
            "email": staff_email,
            "password": "MatKhauStaff123!",
            "fullName": "Nhân viên kiểm thử phân quyền",
            "phone": "0900000088",
            "status": "ACTIVE",
            "permissionCodes": ["customer:read"],
        },
    )
    assert created.status_code == 201, created.text
    staff_id = created.json()["id"]
    assert created.json()["extraPermissionCodes"] == []

    row = (
        await db_session.execute(
            text(
                """
                SELECT u.email, u.full_name, u.phone, u.status, r.code AS role_code
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = :staff_id
                """
            ),
            {"staff_id": staff_id},
        )
    ).mappings().one()
    assert row["email"] == staff_email
    assert row["full_name"] == "Nhân viên kiểm thử phân quyền"
    assert row["phone"] == "0900000088"
    assert row["status"] == "ACTIVE"
    assert row["role_code"] == "STAFF_ADMIN"

    initial_permissions = await api_client.get(
        f"/api/admin/users/{staff_id}/permissions",
        headers=admin_headers,
    )
    assert initial_permissions.status_code == 200, initial_permissions.text
    assert initial_permissions.json()["permissionCodes"] == []

    updated_permissions = await api_client.put(
        f"/api/admin/users/{staff_id}/permissions",
        headers=admin_headers,
        json={"permissionCodes": ["inventory:read", "customer:read", "customer:read"]},
    )
    assert updated_permissions.status_code == 200, updated_permissions.text
    assert updated_permissions.json()["permissionCodes"] == ["customer:read", "inventory:read"]

    persisted_permissions = [
        item[0]
        for item in (
            await db_session.execute(
                text(
                    """
                    SELECT p.code
                    FROM user_permissions up
                    JOIN permissions p ON p.id = up.permission_id
                    WHERE up.user_id = :staff_id
                    ORDER BY p.code
                    """
                ),
                {"staff_id": staff_id},
            )
        ).all()
    ]
    assert persisted_permissions == ["customer:read", "inventory:read"]

    invalid_permissions = await api_client.put(
        f"/api/admin/users/{staff_id}/permissions",
        headers=admin_headers,
        json={"permissionCodes": ["permission:khong-ton-tai"]},
    )
    assert invalid_permissions.status_code == 400, invalid_permissions.text

    self_permissions = await api_client.get(
        f"/api/admin/users/{admin_user['id']}/permissions",
        headers=admin_headers,
    )
    assert self_permissions.status_code == 403, self_permissions.text

    converted_to_customer = await api_client.patch(
        f"/api/admin/users/{staff_id}/role",
        headers=admin_headers,
        json={"role": "CUSTOMER", "status": "ACTIVE"},
    )
    assert converted_to_customer.status_code == 200, converted_to_customer.text

    role_row = (
        await db_session.execute(
            text(
                """
                SELECT r.code AS role_code, COUNT(up.permission_id)::int AS extra_permission_count
                FROM users u
                JOIN roles r ON r.id = u.role_id
                LEFT JOIN user_permissions up ON up.user_id = u.id
                WHERE u.id = :staff_id
                GROUP BY r.code
                """
            ),
            {"staff_id": staff_id},
        )
    ).mappings().one()
    assert role_row["role_code"] == "CUSTOMER"
    assert role_row["extra_permission_count"] == 0

    customer_permission_update = await api_client.put(
        f"/api/admin/users/{staff_id}/permissions",
        headers=admin_headers,
        json={"permissionCodes": ["customer:read"]},
    )
    assert customer_permission_update.status_code == 400, customer_permission_update.text


@pytest.mark.workflow
async def test_admin_role_permission_read_paths_and_restrictions(
    api_client,
    db_session,
    admin_headers,
):
    roles = await api_client.get("/api/admin/roles", headers=admin_headers)
    assert roles.status_code == 200, roles.text
    staff_role = next(item for item in roles.json() if item["code"] == "STAFF_ADMIN")
    customer_role = next(item for item in roles.json() if item["code"] == "CUSTOMER")

    customer_permissions = await api_client.get(
        f"/api/admin/roles/{customer_role['id']}/permissions",
        headers=admin_headers,
    )
    assert customer_permissions.status_code == 200, customer_permissions.text
    assert customer_permissions.json()["code"] == "CUSTOMER"

    staff_update = await api_client.put(
        f"/api/admin/roles/{staff_role['id']}/permissions",
        headers=admin_headers,
        json={"permissionCodes": ["customer:read"]},
    )
    assert staff_update.status_code == 400, staff_update.text

    invalid_customer_update = await api_client.put(
        f"/api/admin/roles/{customer_role['id']}/permissions",
        headers=admin_headers,
        json={"permissionCodes": ["permission:khong-ton-tai"]},
    )
    assert invalid_customer_update.status_code == 400, invalid_customer_update.text

    updated_customer_role = await api_client.put(
        f"/api/admin/roles/{customer_role['id']}/permissions",
        headers=admin_headers,
        json={"permissionCodes": ["customer:read"]},
    )
    assert updated_customer_role.status_code == 200, updated_customer_role.text

    persisted = await db_session.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM role_permissions rp
            JOIN permissions p ON p.id = rp.permission_id
            WHERE rp.role_id = :role_id AND p.code = 'customer:read'
            """
        ),
        {"role_id": customer_role["id"]},
    )
    assert persisted == 1
