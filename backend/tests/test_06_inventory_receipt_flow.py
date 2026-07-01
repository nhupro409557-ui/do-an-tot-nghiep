import json
from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_inventory_receipt_draft_approval_completion_updates_stock(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    product_id = uuid4()
    variant_id = uuid4()
    sku = f"TEST-INV-{uuid4().hex[:8].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, stock_quantity,
                status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'ACCESSORY', 'Hãng kiểm thử',
                500000, 0, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Sản phẩm nhập kho kiểm thử",
            "slug": f"san-pham-nhap-kho-{uuid4().hex[:8]}",
            "sales_config": json.dumps(
                {
                    "imeiPolicy": {"mode": "MANUAL", "trackImei": False},
                    "serialPolicy": {
                        "mode": "MANUAL",
                        "trackSerialNumber": False,
                    },
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
                500000, 500000, 0, TRUE
            )
            """
        ),
        {
            "variant_id": variant_id,
            "product_id": product_id,
            "variant_sku": f"{sku}-DEFAULT",
        },
    )
    await db_session.commit()

    reference_code = f"TEST-IN-{uuid4().hex[:10].upper()}"
    created = await api_client.post(
        "/api/admin/inventory/receipts",
        headers={**admin_headers, "Idempotency-Key": reference_code},
        json={
            "referenceCode": reference_code,
            "receiptReasonCode": "NK_MUA",
            "supplierName": "Nhà cung cấp kiểm thử",
            "qualityStatus": "PASSED",
            "status": "DRAFT",
            "lines": [
                    {
                        "productId": str(product_id),
                        "variantId": str(variant_id),
                        "quantity": 3,
                    "unitCost": 400000,
                    "storageLocationCode": "A-01-01",
                }
            ],
        },
    )
    assert created.status_code == 200, created.text

    for target_status in ("APPROVED", "COMPLETED"):
        changed = await api_client.patch(
            f"/api/admin/inventory/receipts/{reference_code}/status",
            headers=approver_headers,
            json={"status": target_status},
        )
        assert changed.status_code == 200, (
            f"{target_status}: {changed.status_code} {changed.text}"
        )

    document = (
        await db_session.execute(
            text(
                """
                SELECT status, posted_at
                FROM inventory_documents
                WHERE document_no = :reference_code
                """
            ),
            {"reference_code": reference_code},
        )
    ).mappings().one()
    stock = await db_session.scalar(
        text("SELECT stock_quantity FROM products WHERE id = :product_id"),
        {"product_id": product_id},
    )
    assert document["status"] == "COMPLETED"
    assert document["posted_at"] is not None
    assert stock == 3

    levels = await api_client.get(
        "/api/admin/inventory/levels",
        headers=admin_headers,
        params={"search": sku},
    )
    assert levels.status_code == 200, levels.text
    assert sku in levels.text
