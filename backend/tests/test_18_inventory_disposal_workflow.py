import json
from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_disposal_completion_reduces_stock_lots_and_clears_identifiers(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    product_id = uuid4()
    variant_id = uuid4()
    pair_id = uuid4()
    sku = f"DISP-{uuid4().hex[:8].upper()}"
    imei_seed = str(uuid4().int)
    imei1 = ("35" + imei_seed)[:15]
    imei2 = ("86" + imei_seed[::-1])[:15]
    serial_number = f"SN{uuid4().hex[:12].upper()}"
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
            "name": "Sản phẩm hủy tồn kiểm thử",
            "slug": f"san-pham-huy-ton-{uuid4().hex[:8]}",
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
    location_id = await db_session.scalar(text("SELECT id FROM inventory_locations WHERE code = 'A-01-01'"))
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_levels (
                id, product_id, variant_id, location_id,
                on_hand_quantity, reserved_quantity, average_unit_cost
            )
            VALUES (gen_random_uuid(), NULL, :variant_id, :location_id, 1, 0, 9000000)
            """
        ),
        {"variant_id": variant_id, "location_id": location_id},
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
                :source_reference, 1, 1,
                9000000, NOW() - INTERVAL '5 days', 'ACTIVE'
            )
            """
        ),
        {
            "lot_code": f"LOT-DISP-{uuid4().hex[:8]}",
            "variant_id": variant_id,
            "location_id": location_id,
            "source_reference": f"RECEIPT-{sku}",
        },
    )
    for imei, is_primary in ((imei1, True), (imei2, False)):
        await db_session.execute(
            text(
                """
                INSERT INTO product_imeis (
                    id, product_id, variant_id, imei, status,
                    location_id, source_reference, is_primary
                )
                VALUES (
                    gen_random_uuid(), :product_id, :variant_id, :imei, 'IN_STOCK',
                    :location_id, :source_reference, :is_primary
                )
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "imei": imei,
                "location_id": location_id,
                "source_reference": f"RECEIPT-{sku}",
                "is_primary": is_primary,
            },
        )
    await db_session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (
                id, product_id, variant_id, serial_number, status,
                location_id, source_reference
            )
            VALUES (
                gen_random_uuid(), :product_id, :variant_id, :serial_number, 'IN_STOCK',
                :location_id, :source_reference
            )
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "serial_number": serial_number,
            "location_id": location_id,
            "source_reference": f"RECEIPT-{sku}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_identifier_pairs (
                id, product_id, variant_id, imei1, imei2, serial_number, source_reference
            )
            VALUES (
                :id, :product_id, :variant_id, :imei1, :imei2, :serial_number, :source_reference
            )
            """
        ),
        {
            "id": pair_id,
            "product_id": product_id,
            "variant_id": variant_id,
            "imei1": imei1,
            "imei2": imei2,
            "serial_number": serial_number,
            "source_reference": f"RECEIPT-{sku}",
        },
    )
    await db_session.commit()

    reference_code = f"DISP-{uuid4().hex[:10].upper()}"
    created = await api_client.post(
        "/api/admin/inventory/disposals",
        headers=admin_headers,
        json={
            "referenceCode": reference_code,
            "dispositionType": "SCRAP",
            "reason": "Hàng hỏng không thể bán",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id),
                    "locationId": str(location_id),
                    "quantity": 1,
                    "imeis": [imei1],
                    "serialNumbers": [serial_number],
                }
            ],
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["status"] == "DRAFT"

    approved = await api_client.patch(
        f"/api/admin/inventory/disposals/{reference_code}/status",
        headers=approver_headers,
        json={"status": "APPROVED"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["postedLineCount"] == 0
    level_after_approval = await db_session.scalar(
        text("SELECT on_hand_quantity FROM inventory_levels WHERE variant_id = :variant_id"),
        {"variant_id": variant_id},
    )
    assert level_after_approval == 1

    completed = await api_client.patch(
        f"/api/admin/inventory/disposals/{reference_code}/status",
        headers=approver_headers,
        json={"status": "COMPLETED"},
    )
    assert completed.status_code == 200, completed.text
    payload = completed.json()
    assert payload["postedLineCount"] == 1
    assert set(payload["lines"][0]["imeis"]) == {imei1, imei2}
    assert payload["lines"][0]["serialNumbers"] == [serial_number]
    assert sum(item["quantity"] for item in payload["lines"][0]["consumedLots"]) == 1

    level_after_completion = await db_session.scalar(
        text("SELECT on_hand_quantity FROM inventory_levels WHERE variant_id = :variant_id"),
        {"variant_id": variant_id},
    )
    assert level_after_completion == 0
    variant_stock = await db_session.scalar(
        text("SELECT stock_quantity FROM product_variants WHERE id = :variant_id"),
        {"variant_id": variant_id},
    )
    assert variant_stock == 0
    lot_remaining = await db_session.scalar(
        text("SELECT COALESCE(SUM(remaining_quantity), 0)::int FROM inventory_lots WHERE variant_id = :variant_id"),
        {"variant_id": variant_id},
    )
    assert lot_remaining == 0
    imei_rows = (
        await db_session.execute(
            text("SELECT imei, status, location_id FROM product_imeis WHERE variant_id = :variant_id"),
            {"variant_id": variant_id},
        )
    ).mappings().all()
    assert {row["imei"]: row["status"] for row in imei_rows} == {imei1: "SCRAP", imei2: "SCRAP"}
    assert all(row["location_id"] is None for row in imei_rows)
    serial_row = (
        await db_session.execute(
            text("SELECT status, location_id FROM product_serial_numbers WHERE serial_number = :serial_number"),
            {"serial_number": serial_number},
        )
    ).mappings().one()
    assert serial_row["status"] == "SCRAP"
    assert serial_row["location_id"] is None
