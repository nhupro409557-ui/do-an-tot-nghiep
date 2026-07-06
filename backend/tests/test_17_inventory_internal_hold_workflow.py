import json
from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_internal_hold_approval_and_completion_adjust_reserved_quantity(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    product_id = uuid4()
    variant_id = uuid4()
    sku = f"HOLD-{uuid4().hex[:8].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'ACCESSORY', 'Thương hiệu kiểm thử',
                500000, 500000, 5, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Sản phẩm giữ nội bộ kiểm thử",
            "slug": f"san-pham-giu-noi-bo-{uuid4().hex[:8]}",
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
                500000, 500000, 5, TRUE
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
            VALUES (gen_random_uuid(), NULL, :variant_id, :location_id, 5, 0, 400000)
            """
        ),
        {"variant_id": variant_id, "location_id": location_id},
    )
    await db_session.commit()

    reference_code = f"HOLD-{uuid4().hex[:10].upper()}"
    created = await api_client.post(
        "/api/admin/inventory/internal-holds",
        headers=admin_headers,
        json={
            "referenceCode": reference_code,
            "holdType": "QC_HOLD",
            "reason": "Giữ hàng để kiểm tra chất lượng",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id),
                    "locationId": str(location_id),
                    "quantity": 2,
                }
            ],
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["status"] == "DRAFT"

    reserved_after_create = await db_session.scalar(
        text("SELECT reserved_quantity FROM inventory_levels WHERE variant_id = :variant_id"),
        {"variant_id": variant_id},
    )
    assert reserved_after_create == 0

    approved = await api_client.patch(
        f"/api/admin/inventory/internal-holds/{reference_code}/status",
        headers=approver_headers,
        json={"status": "APPROVED"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["postedLineCount"] == 1
    assert approved.json()["lines"][0]["reservedQuantity"] == 2

    reserved_after_approval = await db_session.scalar(
        text("SELECT reserved_quantity FROM inventory_levels WHERE variant_id = :variant_id"),
        {"variant_id": variant_id},
    )
    assert reserved_after_approval == 2

    suggestions = await api_client.get(
        f"/api/admin/inventory/issue-suggestions?productId={product_id}&variantId={variant_id}&quantity=5",
        headers=admin_headers,
    )
    assert suggestions.status_code == 200, suggestions.text
    assert sum(item["suggestedQuantity"] for item in suggestions.json()) == 3

    completed = await api_client.patch(
        f"/api/admin/inventory/internal-holds/{reference_code}/status",
        headers=approver_headers,
        json={"status": "COMPLETED"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["postedLineCount"] == 1
    assert completed.json()["lines"][0]["reservedQuantity"] == 0

    reserved_after_completion = await db_session.scalar(
        text("SELECT reserved_quantity FROM inventory_levels WHERE variant_id = :variant_id"),
        {"variant_id": variant_id},
    )
    assert reserved_after_completion == 0
