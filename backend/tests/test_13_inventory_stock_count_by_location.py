import json
from uuid import uuid4

import pytest
from sqlalchemy import text


async def _seed_variant_on_shelves(db_session, *, track_imei: bool, first_quantity: int, second_quantity: int):
    product_id = uuid4()
    variant_id = uuid4()
    sku = f"COUNT-{uuid4().hex[:8].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'ACCESSORY', 'Thương hiệu kiểm thử',
                500000, 500000, :stock_quantity, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Sản phẩm kiểm kê theo kệ",
            "slug": f"san-pham-kiem-ke-{uuid4().hex[:8]}",
            "stock_quantity": first_quantity + second_quantity,
            "sales_config": json.dumps(
                {
                    "imeiPolicy": {"mode": "MANUAL", "trackImei": track_imei},
                    "serialPolicy": {"mode": "MANUAL", "trackSerialNumber": False},
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
                500000, 500000, :stock_quantity, TRUE
            )
            """
        ),
        {
            "variant_id": variant_id,
            "product_id": product_id,
            "variant_sku": f"{sku}-DEFAULT",
            "stock_quantity": first_quantity + second_quantity,
        },
    )
    locations = (
        await db_session.execute(
            text("SELECT id, code FROM inventory_locations WHERE code IN ('A-01-01', 'A-01-02')")
        )
    ).mappings().all()
    location_ids = {row["code"]: row["id"] for row in locations}
    assert set(location_ids) == {"A-01-01", "A-01-02"}
    for code, quantity in (("A-01-01", first_quantity), ("A-01-02", second_quantity)):
        await db_session.execute(
            text(
                """
                INSERT INTO inventory_levels (
                    id, product_id, variant_id, location_id,
                    on_hand_quantity, reserved_quantity, average_unit_cost
                )
                VALUES (gen_random_uuid(), NULL, :variant_id, :location_id, :quantity, 0, 400000)
                """
            ),
            {
                "variant_id": variant_id,
                "location_id": location_ids[code],
                "quantity": quantity,
            },
        )
    await db_session.commit()
    return product_id, variant_id, location_ids


@pytest.mark.workflow
async def test_stock_count_updates_total_by_shelf_variance(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    product_id, variant_id, location_ids = await _seed_variant_on_shelves(
        db_session,
        track_imei=False,
        first_quantity=4,
        second_quantity=6,
    )
    reference_code = f"COUNT-{uuid4().hex[:10].upper()}"
    created = await api_client.post(
        "/api/admin/inventory/stock-counts",
        headers=admin_headers,
        json={
            "referenceCode": reference_code,
            "reason": "KIEM_KE_THEO_KE",
            "locationCode": "A-01-01",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id),
                    "expectedQuantity": 999,
                    "countedQuantity": 3,
                }
            ],
        },
    )
    assert created.status_code == 200, created.text

    approved = await api_client.patch(
        f"/api/admin/inventory/stock-counts/{reference_code}/status",
        headers=approver_headers,
        json={"status": "APPROVED"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["lines"][0]["expectedQuantity"] == 4
    assert approved.json()["lines"][0]["oldQuantity"] == 10
    assert approved.json()["lines"][0]["newQuantity"] == 9
    assert approved.json()["lines"][0]["varianceQuantity"] == -1

    variant_quantity = await db_session.scalar(
        text("SELECT stock_quantity FROM product_variants WHERE id = :variant_id"),
        {"variant_id": variant_id},
    )
    assert variant_quantity == 9
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
    levels = {row["location_id"]: row["on_hand_quantity"] for row in level_rows}
    assert levels[location_ids["A-01-01"]] == 3
    assert levels[location_ids["A-01-02"]] == 6


@pytest.mark.workflow
async def test_stock_count_uses_scanned_imeis_and_blocks_identifier_mismatch(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    product_id, variant_id, location_ids = await _seed_variant_on_shelves(
        db_session,
        track_imei=True,
        first_quantity=2,
        second_quantity=0,
    )
    imeis = ["350000000000001", "350000000000002"]
    serial_numbers = ["COUNT-SN-001", "COUNT-SN-002"]
    for imei, serial_number in zip(imeis, serial_numbers, strict=True):
        await db_session.execute(
            text(
                """
                INSERT INTO product_imeis (
                    id, product_id, variant_id, imei, status, location_id
                )
                VALUES (gen_random_uuid(), :product_id, :variant_id, :imei, 'IN_STOCK', :location_id)
                """
            ),
            {
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
                VALUES (gen_random_uuid(), :product_id, :variant_id, :serial_number, 'IN_STOCK', :location_id)
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "serial_number": serial_number,
                "location_id": location_ids["A-01-01"],
            },
        )
    await db_session.commit()

    reference_code = f"COUNT-IMEI-{uuid4().hex[:8].upper()}"
    created = await api_client.post(
        "/api/admin/inventory/stock-counts",
        headers=admin_headers,
        json={
            "referenceCode": reference_code,
            "reason": "KIEM_KE_IMEI_THEO_KE",
            "locationCode": "A-01-01",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id),
                    "expectedQuantity": 2,
                    "countedQuantity": 99,
                    "imeis": [imeis[0]],
                    "serialNumbers": [serial_numbers[0]],
                }
            ],
        },
    )
    assert created.status_code == 200, created.text

    listed = await api_client.get(
        "/api/admin/inventory/stock-counts",
        headers=admin_headers,
        params={"search": reference_code},
    )
    assert listed.status_code == 200, listed.text
    line = listed.json()[0]["lines"][0]
    assert line["countedQuantity"] == 1
    assert line["imeis"] == [imeis[0]]
    assert line["missingImeis"] == [imeis[1]]
    assert line["serialNumbers"] == [serial_numbers[0]]
    assert line["missingSerialNumbers"] == [serial_numbers[1]]

    approved = await api_client.patch(
        f"/api/admin/inventory/stock-counts/{reference_code}/status",
        headers=approver_headers,
        json={"status": "APPROVED"},
    )
    assert approved.status_code == 409, approved.text
    assert "mã quét chưa khớp" in approved.text

    level_quantity = await db_session.scalar(
        text(
            """
            SELECT on_hand_quantity
            FROM inventory_levels
            WHERE variant_id = :variant_id AND location_id = :location_id
            """
        ),
        {
            "variant_id": variant_id,
            "location_id": location_ids["A-01-01"],
        },
    )
    assert level_quantity == 2


@pytest.mark.workflow
async def test_cycle_count_due(api_client, db_session, admin_headers):
    # Call the GET endpoint
    res = await api_client.get(
        "/api/admin/inventory/stock-counts/due",
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data, list)

    # If there are active products, check schema of the first item
    if len(data) > 0:
        item = data[0]
        assert "productId" in item
        assert "sku" in item
        assert "name" in item
        assert "cycleCountDays" in item
        assert "lastCountedAt" in item
        assert "daysSinceLastCount" in item
        assert "nextCountDueDate" in item
        assert "isDue" in item

        # Test search filter
        res_search = await api_client.get(
            "/api/admin/inventory/stock-counts/due",
            headers=admin_headers,
            params={"search": item["sku"]},
        )
        assert res_search.status_code == 200
        search_data = res_search.json()
        assert len(search_data) > 0
        assert search_data[0]["sku"] == item["sku"]
