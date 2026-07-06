import json
from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_identifier_location_requests_require_approval_without_changing_stock(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    product_id = uuid4()
    variant_id = uuid4()
    sku = f"LOC-{uuid4().hex[:8].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'ACCESSORY', 'Thương hiệu kiểm thử',
                700000, 700000, 2, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Sản phẩm gán vị trí mã",
            "slug": f"san-pham-gan-vi-tri-{uuid4().hex[:8]}",
            "sales_config": json.dumps(
                {
                    "imeiPolicy": {"mode": "MANUAL", "trackImei": True},
                    "serialPolicy": {"mode": "MANUAL", "trackSerialNumber": True},
                }
            ),
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_variants (
                id, product_id, sku, configuration, price, sale_price,
                stock_quantity, is_active
            )
            VALUES (
                :variant_id, :product_id, :variant_sku, 'Mặc định',
                700000, 700000, 2, TRUE
            )
            """
        ),
        {
            "variant_id": variant_id,
            "product_id": product_id,
            "variant_sku": f"{sku}-DEFAULT",
        },
    )
    locations = (
        await db_session.execute(
            text("SELECT id, code FROM inventory_locations WHERE code IN ('A-01-01', 'A-01-02')")
        )
    ).mappings().all()
    location_ids = {row["code"]: row["id"] for row in locations}
    for code in ("A-01-01", "A-01-02"):
        await db_session.execute(
            text(
                """
                INSERT INTO inventory_levels (
                    id, product_id, variant_id, location_id,
                    on_hand_quantity, reserved_quantity, average_unit_cost
                )
                VALUES (gen_random_uuid(), NULL, :variant_id, :location_id, 1, 0, 600000)
                """
            ),
            {"variant_id": variant_id, "location_id": location_ids[code]},
        )

    imei1_id = uuid4()
    imei1 = "350000000000101"
    imei2_id = uuid4()
    imei2 = "350000000000102"
    paired_serial_id = uuid4()
    paired_serial_number = "LOCATION-PAIR-001"
    serial_id = uuid4()
    serial_number = "LOCATION-STANDALONE-001"
    for imei_id, imei in ((imei1_id, imei1), (imei2_id, imei2)):
        await db_session.execute(
            text(
                """
                INSERT INTO product_imeis (
                    id, product_id, variant_id, imei, status, location_id
                )
                VALUES (:id, :product_id, :variant_id, :imei, 'IN_STOCK', :location_id)
                """
            ),
            {
                "id": imei_id,
                "product_id": product_id,
                "variant_id": variant_id,
                "imei": imei,
                "location_id": location_ids["A-01-01"],
            },
        )
    await db_session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (
                id, product_id, variant_id, serial_number, status, location_id
            )
            VALUES (:id, :product_id, :variant_id, :serial_number, 'IN_STOCK', :location_id)
            """
        ),
        {
            "id": paired_serial_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "serial_number": paired_serial_number,
            "location_id": location_ids["A-01-01"],
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (
                id, product_id, variant_id, serial_number, status, location_id
            )
            VALUES (:id, :product_id, :variant_id, :serial_number, 'IN_STOCK', NULL)
            """
        ),
        {
            "id": serial_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "serial_number": serial_number,
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_identifier_pairs (
                id, product_id, variant_id, imei1, imei2, serial_number
            )
            VALUES (gen_random_uuid(), :product_id, :variant_id, :imei1, :imei2, :serial_number)
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "imei1": imei1,
            "imei2": imei2,
            "serial_number": paired_serial_number,
        },
    )
    await db_session.commit()

    imei_request = await api_client.post(
        "/api/admin/inventory/identifier-location-requests",
        headers=admin_headers,
        json={
            "identifierType": "IMEI",
            "identifierId": str(imei2_id),
            "identifierValue": imei2,
            "productId": str(product_id),
            "variantId": str(variant_id),
            "newLocationId": str(location_ids["A-01-02"]),
            "reason": "Chuyển mã về đúng kệ thực tế",
        },
    )
    assert imei_request.status_code == 200, imei_request.text

    duplicate_request = await api_client.post(
        "/api/admin/inventory/identifier-location-requests",
        headers=admin_headers,
        json={
            "identifierType": "IMEI",
            "identifierId": str(imei1_id),
            "productId": str(product_id),
            "variantId": str(variant_id),
            "newLocationId": str(location_ids["A-01-02"]),
            "reason": "Yêu cầu trùng cần bị chặn",
        },
    )
    assert duplicate_request.status_code == 409, duplicate_request.text

    serial_request = await api_client.post(
        "/api/admin/inventory/identifier-location-requests",
        headers=admin_headers,
        json={
            "identifierType": "SERIAL",
            "identifierValue": serial_number,
            "productId": str(product_id),
            "variantId": str(variant_id),
            "newLocationId": str(location_ids["A-01-01"]),
            "reason": "Bổ sung kệ còn thiếu cho serial",
        },
    )
    assert serial_request.status_code == 200, serial_request.text

    pending = await api_client.get(
        "/api/admin/inventory/identifier-location-requests",
        headers=admin_headers,
        params={"status": "PENDING"},
    )
    assert pending.status_code == 200, pending.text
    assert len(pending.json()) == 2

    for request_id in (imei_request.json()["requestId"], serial_request.json()["requestId"]):
        approved = await api_client.patch(
            f"/api/admin/inventory/identifier-location-requests/{request_id}",
            headers=approver_headers,
            json={"decision": "APPROVED", "note": "Đã đối chiếu thực tế"},
        )
        assert approved.status_code == 200, approved.text

    imei_locations = (
        await db_session.execute(
            text("SELECT imei, location_id FROM product_imeis WHERE id IN (:imei1_id, :imei2_id)"),
            {"imei1_id": imei1_id, "imei2_id": imei2_id},
        )
    ).mappings().all()
    paired_serial_location = await db_session.scalar(
        text("SELECT location_id FROM product_serial_numbers WHERE id = :id"),
        {"id": paired_serial_id},
    )
    serial_location = await db_session.scalar(
        text("SELECT location_id FROM product_serial_numbers WHERE id = :id"),
        {"id": serial_id},
    )
    assert {row["imei"]: row["location_id"] for row in imei_locations} == {
        imei1: location_ids["A-01-02"],
        imei2: location_ids["A-01-02"],
    }
    assert paired_serial_location == location_ids["A-01-02"]
    assert serial_location == location_ids["A-01-01"]

    levels = (
        await db_session.execute(
            text(
                """
                SELECT location_id, on_hand_quantity
                FROM inventory_levels
                WHERE variant_id = :variant_id
                """
            ),
            {"variant_id": variant_id},
        )
    ).mappings().all()
    assert {row["location_id"]: row["on_hand_quantity"] for row in levels} == {
        location_ids["A-01-01"]: 1,
        location_ids["A-01-02"]: 1,
    }
