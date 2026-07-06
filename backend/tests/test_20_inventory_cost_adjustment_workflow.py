import json
from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_cost_adjustment_updates_cost_without_changing_quantity(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    product_id = uuid4()
    variant_id = uuid4()
    location_id = uuid4()
    lot_id = uuid4()
    sku = f"COST-{uuid4().hex[:8].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'PHONE', 'Thương hiệu kiểm thử',
                12000000, 12000000, 2, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Sản phẩm điều chỉnh giá vốn kiểm thử",
            "slug": f"san-pham-gia-von-{uuid4().hex[:8]}",
            "sales_config": json.dumps({}),
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
                12000000, 12000000, 2, TRUE
            )
            """
        ),
        {"variant_id": variant_id, "product_id": product_id, "variant_sku": f"{sku}-DEFAULT"},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_locations (id, code, name, location_type, status, is_default)
            VALUES (:location_id, :location_code, 'Kệ giá vốn kiểm thử', 'WAREHOUSE', 'ACTIVE', FALSE)
            """
        ),
        {"location_id": location_id, "location_code": f"GV-{uuid4().hex[:6].upper()}"},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_levels (
                id, product_id, variant_id, location_id,
                on_hand_quantity, reserved_quantity, average_unit_cost
            )
            VALUES (gen_random_uuid(), NULL, :variant_id, :location_id, 2, 0, 1000000)
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
                :lot_id, :lot_code, NULL, :variant_id, :location_id,
                :source_reference, 2, 2,
                1000000, NOW() - INTERVAL '3 days', 'ACTIVE'
            )
            """
        ),
        {
            "lot_id": lot_id,
            "lot_code": f"LOT-COST-{uuid4().hex[:8]}",
            "variant_id": variant_id,
            "location_id": location_id,
            "source_reference": f"RECEIPT-{sku}",
        },
    )
    await db_session.commit()

    reference_code = f"GV-{uuid4().hex[:10].upper()}"
    created = await api_client.post(
        "/api/admin/inventory/cost-adjustments",
        headers=admin_headers,
        json={
            "referenceCode": reference_code,
            "reason": "Đối soát lại giá vốn sau nhập kho",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id),
                    "locationId": str(location_id),
                    "newAverageUnitCost": 1250000,
                    "lotCosts": [{"lotId": str(lot_id), "newUnitCost": 1250000}],
                }
            ],
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["status"] == "DRAFT"

    approved = await api_client.patch(
        f"/api/admin/inventory/cost-adjustments/{reference_code}/status",
        headers=approver_headers,
        json={"status": "APPROVED"},
    )
    assert approved.status_code == 200, approved.text
    level_after_approval = (
        await db_session.execute(
            text("SELECT on_hand_quantity, average_unit_cost FROM inventory_levels WHERE variant_id = :variant_id"),
            {"variant_id": variant_id},
        )
    ).mappings().one()
    assert level_after_approval["on_hand_quantity"] == 2
    assert float(level_after_approval["average_unit_cost"]) == 1000000

    completed = await api_client.patch(
        f"/api/admin/inventory/cost-adjustments/{reference_code}/status",
        headers=approver_headers,
        json={"status": "COMPLETED"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["postedLineCount"] == 1

    level_after_completion = (
        await db_session.execute(
            text("SELECT on_hand_quantity, reserved_quantity, average_unit_cost FROM inventory_levels WHERE variant_id = :variant_id"),
            {"variant_id": variant_id},
        )
    ).mappings().one()
    assert level_after_completion["on_hand_quantity"] == 2
    assert level_after_completion["reserved_quantity"] == 0
    assert float(level_after_completion["average_unit_cost"]) == 1250000
    lot_cost = await db_session.scalar(text("SELECT unit_cost FROM inventory_lots WHERE id = :lot_id"), {"lot_id": lot_id})
    assert float(lot_cost) == 1250000
    log_row = (
        await db_session.execute(
            text(
                """
                SELECT delta, reason, unit_cost
                FROM inventory_adjustment_logs
                WHERE reference_code = :reference_code
                """
            ),
            {"reference_code": reference_code},
        )
    ).mappings().one()
    assert log_row["delta"] == 0
    assert log_row["reason"] == "COST_ADJUSTMENT"
    assert float(log_row["unit_cost"]) == 1250000
