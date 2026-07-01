from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
@pytest.mark.parametrize(
    ("resource", "payload", "table", "code_column"),
    [
        (
            "brands",
            {"name": "Hãng kiểm thử", "code": "BRAND_TEST"},
            "brands",
            "code",
        ),
        (
            "categories",
            {"name": "Danh mục kiểm thử", "code": "CATEGORY_TEST"},
            "categories",
            "code",
        ),
        (
            "suppliers",
            {
                "name": "Nhà cung cấp kiểm thử",
                "code": "SUPPLIER_TEST",
                "email": "supplier@example.com",
            },
            "suppliers",
            "code",
        ),
    ],
)
async def test_reference_data_front_to_api_to_database(
    api_client,
    db_session,
    admin_headers,
    resource,
    payload,
    table,
    code_column,
):
    unique = uuid4().hex[:8].upper()
    expected_code = f"{payload['code']}_{unique}"
    request_payload = {**payload, "code": expected_code}

    created = await api_client.post(
        f"/api/admin/{resource}",
        headers=admin_headers,
        json=request_payload,
    )
    assert created.status_code == 201, created.text

    stored = await db_session.scalar(
        text(f"SELECT COUNT(*) FROM {table} WHERE {code_column} = :code"),
        {"code": expected_code},
    )
    assert stored == 1

    listed = await api_client.get(f"/api/admin/{resource}", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    assert expected_code in listed.text
