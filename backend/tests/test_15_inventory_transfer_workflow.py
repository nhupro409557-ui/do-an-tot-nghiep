import json
from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_transfer_approval_and_completion_move_levels_and_lots(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    product_id = uuid4()
    variant_id = uuid4()
    sku = f"TRANSFER-{uuid4().hex[:8].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'ACCESSORY', 'Thương hiệu kiểm thử',
                900000, 900000, 5, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Sản phẩm chuyển kệ kiểm thử",
            "slug": f"san-pham-chuyen-ke-{uuid4().hex[:8]}",
            "sales_config": json.dumps(
                {
                    "imeiPolicy": {"mode": "MANUAL", "trackImei": False},
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
                900000, 900000, 5, TRUE
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
    for code, quantity in (("A-01-01", 3), ("A-01-02", 2)):
        await db_session.execute(
            text(
                """
                INSERT INTO inventory_levels (
                    id, product_id, variant_id, location_id,
                    on_hand_quantity, reserved_quantity, average_unit_cost
                )
                VALUES (gen_random_uuid(), NULL, :variant_id, :location_id, :quantity, 0, 750000)
                """
            ),
            {
                "variant_id": variant_id,
                "location_id": location_ids[code],
                "quantity": quantity,
            },
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
                    :source_reference, :quantity, :quantity,
                    750000, NOW() - INTERVAL '10 days', 'ACTIVE'
                )
                """
            ),
            {
                "lot_code": f"LOT-{code}-{uuid4().hex[:8]}",
                "variant_id": variant_id,
                "location_id": location_ids[code],
                "source_reference": f"RECEIPT-{code}",
                "quantity": quantity,
            },
        )
    await db_session.commit()

    reference_code = f"TRF-{uuid4().hex[:10].upper()}"
    created = await api_client.post(
        "/api/admin/inventory/transfers",
        headers=admin_headers,
        json={
            "referenceCode": reference_code,
            "reason": "TACH_KE",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id),
                    "fromLocationId": str(location_ids["A-01-01"]),
                    "toLocationId": str(location_ids["A-01-02"]),
                    "quantity": 1,
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
    assert approved.json()["postedLineCount"] == 0

    levels_after_approval = (
        await db_session.execute(
            text("SELECT location_id, on_hand_quantity FROM inventory_levels WHERE variant_id = :variant_id"),
            {"variant_id": variant_id},
        )
    ).mappings().all()
    assert {row["location_id"]: row["on_hand_quantity"] for row in levels_after_approval} == {
        location_ids["A-01-01"]: 3,
        location_ids["A-01-02"]: 2,
    }

    completed = await api_client.patch(
        f"/api/admin/inventory/transfers/{reference_code}/status",
        headers=approver_headers,
        json={"status": "COMPLETED"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["postedLineCount"] == 1
    assert sum(item["quantity"] for item in completed.json()["lines"][0]["movedLots"]) == 1

    levels_after_completion = (
        await db_session.execute(
            text("SELECT location_id, on_hand_quantity FROM inventory_levels WHERE variant_id = :variant_id"),
            {"variant_id": variant_id},
        )
    ).mappings().all()
    assert {row["location_id"]: row["on_hand_quantity"] for row in levels_after_completion} == {
        location_ids["A-01-01"]: 2,
        location_ids["A-01-02"]: 3,
    }
    variant_quantity = await db_session.scalar(
        text("SELECT stock_quantity FROM product_variants WHERE id = :variant_id"),
        {"variant_id": variant_id},
    )
    assert variant_quantity == 5
    lot_totals = (
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
    assert {row["location_id"]: row["quantity"] for row in lot_totals} == {
        location_ids["A-01-01"]: 2,
        location_ids["A-01-02"]: 3,
    }

    repeated = await api_client.patch(
        f"/api/admin/inventory/transfers/{reference_code}/status",
        headers=approver_headers,
        json={"status": "COMPLETED"},
    )
    assert repeated.status_code == 400, repeated.text
