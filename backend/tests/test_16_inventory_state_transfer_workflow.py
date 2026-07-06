import json
from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_state_transfer_updates_sellable_stock_identifiers_lots_and_fifo(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    product_id = uuid4()
    variant_id = uuid4()
    sku = f"STATE-{uuid4().hex[:8].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'PHONE', 'Thương hiệu kiểm thử',
                12000000, 12000000, 1, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Điện thoại điều chuyển trạng thái",
            "slug": f"dien-thoai-dieu-chuyen-trang-thai-{uuid4().hex[:8]}",
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
                12000000, 12000000, 1, TRUE
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
            text(
                """
                SELECT DISTINCT ON (purpose) id, code, purpose
                FROM inventory_locations
                WHERE status = 'ACTIVE'
                  AND purpose IN ('STORAGE', 'DAMAGED')
                ORDER BY purpose, sort_order, code
                """
            )
        )
    ).mappings().all()
    location_by_purpose = {row["purpose"]: row for row in locations}
    storage_location = location_by_purpose["STORAGE"]
    damaged_location = location_by_purpose["DAMAGED"]

    await db_session.execute(
        text(
            """
            INSERT INTO inventory_levels (
                id, product_id, variant_id, location_id,
                on_hand_quantity, reserved_quantity, average_unit_cost
            )
            VALUES (gen_random_uuid(), NULL, :variant_id, :location_id, 1, 0, 10000000)
            """
        ),
        {"variant_id": variant_id, "location_id": storage_location["id"]},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_lots (
                id, lot_code, product_id, variant_id, location_id,
                source_reference, initial_quantity, remaining_quantity,
                unit_cost, received_at, status
            )
            VALUES (
                gen_random_uuid(), :lot_code, NULL, :variant_id, :location_id,
                :source_reference, 1, 1, 10000000, NOW() - INTERVAL '5 days', 'ACTIVE'
            )
            """
        ),
        {
            "lot_code": f"LOT-{uuid4().hex[:10].upper()}",
            "variant_id": variant_id,
            "location_id": storage_location["id"],
            "source_reference": f"RECEIPT-{uuid4().hex[:8].upper()}",
        },
    )

    imei1 = "350000000001601"
    imei2 = "350000000001602"
    serial_number = "STATE-TRANSFER-001"
    for imei in (imei1, imei2):
        await db_session.execute(
            text(
                """
                INSERT INTO product_imeis (
                    id, product_id, variant_id, imei, status, location_id
                )
                VALUES (
                    gen_random_uuid(), :product_id, :variant_id, :imei,
                    'IN_STOCK', :location_id
                )
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "imei": imei,
                "location_id": storage_location["id"],
            },
        )
    await db_session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (
                id, product_id, variant_id, serial_number, status, location_id
            )
            VALUES (
                gen_random_uuid(), :product_id, :variant_id, :serial_number,
                'IN_STOCK', :location_id
            )
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "serial_number": serial_number,
            "location_id": storage_location["id"],
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_identifier_pairs (
                id, product_id, variant_id, imei1, imei2, serial_number
            )
            VALUES (
                gen_random_uuid(), :product_id, :variant_id, :imei1, :imei2, :serial_number
            )
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "imei1": imei1,
            "imei2": imei2,
            "serial_number": serial_number,
        },
    )
    await db_session.commit()

    async def transfer(reference_code, from_location_id, to_location_id):
        created = await api_client.post(
            "/api/admin/inventory/transfers",
            headers=admin_headers,
            json={
                "referenceCode": reference_code,
                "reason": "CHUYEN_TRANG_THAI",
                "lines": [
                    {
                        "productId": str(product_id),
                        "variantId": str(variant_id),
                        "fromLocationId": str(from_location_id),
                        "toLocationId": str(to_location_id),
                        "quantity": 1,
                        "imeis": [imei1],
                        "serialNumbers": [serial_number],
                    }
                ],
            },
        )
        assert created.status_code == 200, created.text
        approved = await api_client.patch(
            f"/api/admin/inventory/transfers/{reference_code}/status",
            headers=approver_headers,
            json={"status": "APPROVED"},
        )
        assert approved.status_code == 200, approved.text
        completed = await api_client.patch(
            f"/api/admin/inventory/transfers/{reference_code}/status",
            headers=approver_headers,
            json={"status": "COMPLETED"},
        )
        assert completed.status_code == 200, completed.text
        return completed.json()

    moved_to_damaged = await transfer(
        f"STATE-ERR-{uuid4().hex[:8].upper()}",
        storage_location["id"],
        damaged_location["id"],
    )
    assert moved_to_damaged["lines"][0]["targetIdentifierStatus"] == "DEFECTIVE_RETURNED"
    assert set(moved_to_damaged["lines"][0]["imeis"]) == {imei1, imei2}

    identifier_rows = (
        await db_session.execute(
            text(
                """
                SELECT imei AS code, status, location_id
                FROM product_imeis
                WHERE product_id = :product_id
                UNION ALL
                SELECT serial_number AS code, status, location_id
                FROM product_serial_numbers
                WHERE product_id = :product_id
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().all()
    assert {row["code"] for row in identifier_rows} == {imei1, imei2, serial_number}
    assert all(row["status"] == "DEFECTIVE_RETURNED" for row in identifier_rows)
    assert all(row["location_id"] == damaged_location["id"] for row in identifier_rows)
    assert await db_session.scalar(
        text("SELECT stock_quantity FROM product_variants WHERE id = :variant_id"),
        {"variant_id": variant_id},
    ) == 0

    issue_suggestions = await api_client.get(
        "/api/admin/inventory/issue-suggestions",
        headers=admin_headers,
        params={
            "productId": str(product_id),
            "variantId": str(variant_id),
            "quantity": 1,
        },
    )
    assert issue_suggestions.status_code == 200, issue_suggestions.text
    assert issue_suggestions.json() == []

    moved_to_storage = await transfer(
        f"STATE-RESTORE-{uuid4().hex[:8].upper()}",
        damaged_location["id"],
        storage_location["id"],
    )
    assert moved_to_storage["lines"][0]["targetIdentifierStatus"] == "IN_STOCK"
    restored_rows = (
        await db_session.execute(
            text(
                """
                SELECT status, location_id
                FROM product_imeis
                WHERE product_id = :product_id
                UNION ALL
                SELECT status, location_id
                FROM product_serial_numbers
                WHERE product_id = :product_id
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().all()
    assert all(row["status"] == "IN_STOCK" for row in restored_rows)
    assert all(row["location_id"] == storage_location["id"] for row in restored_rows)
    assert await db_session.scalar(
        text("SELECT stock_quantity FROM product_variants WHERE id = :variant_id"),
        {"variant_id": variant_id},
    ) == 1

    level_rows = (
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
    quantities = {row["location_id"]: row["on_hand_quantity"] for row in level_rows}
    assert quantities[storage_location["id"]] == 1
    assert quantities[damaged_location["id"]] == 0
    assert sum(quantities.values()) == 1

    lot_rows = (
        await db_session.execute(
            text(
                """
                SELECT location_id, SUM(remaining_quantity)::int AS quantity
                FROM inventory_lots
                WHERE variant_id = :variant_id AND status = 'ACTIVE'
                GROUP BY location_id
                """
            ),
            {"variant_id": variant_id},
        )
    ).mappings().all()
    lot_quantities = {row["location_id"]: row["quantity"] for row in lot_rows}
    assert lot_quantities[storage_location["id"]] == 1
    assert lot_quantities.get(damaged_location["id"], 0) == 0
