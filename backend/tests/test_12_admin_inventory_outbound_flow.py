import json
from uuid import uuid4

import pytest
from sqlalchemy import text


async def _seed_stocked_variant(api_client, db_session, admin_headers, approver_headers):
    product_id = uuid4()
    variant_id = uuid4()
    sku = f"TEST-OUT-{uuid4().hex[:8].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'ACCESSORY', 'Thương hiệu kiểm thử',
                880000, 880000, 0, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Sản phẩm xuất kho kiểm thử",
            "slug": f"san-pham-xuat-kho-{uuid4().hex[:8]}",
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
                880000, 880000, 0, TRUE
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

    reference_code = f"TEST-IN-OUT-{uuid4().hex[:8].upper()}"
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
                    "quantity": 5,
                    "unitCost": 700000,
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
        assert changed.status_code == 200, changed.text

    return product_id, variant_id, sku


async def _create_cod_order(api_client, customer_headers, customer_user, product_id, variant_id, sku):
    idempotency_key = f"admin-outbound-order-{uuid4().hex}"
    created = await api_client.post(
        "/api/orders",
        headers={**customer_headers, "Idempotency-Key": idempotency_key},
        json={
            "user_id": customer_user["id"],
            "items": [
                {
                    "product_id": str(product_id),
                    "variant_id": str(variant_id),
                    "product_name": f"Sản phẩm xuất kho kiểm thử {sku}",
                    "quantity": 2,
                    "unit_price": 880000,
                }
            ],
            "shipping": {
                "recipient_name": "Khách hàng kiểm thử outbound",
                "recipient_phone": "0900000004",
                "recipient_email": customer_user["email"],
                "shipping_address": "456 Đường kiểm thử, Thành phố Hồ Chí Minh",
            },
            "payment_method": "COD",
            "idempotency_key": idempotency_key,
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["order_id"]


@pytest.mark.workflow
async def test_admin_outbound_picking_completion_decrements_stock_and_ships_order(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
    customer_headers,
    customer_user,
):
    product_id, variant_id, sku = await _seed_stocked_variant(
        api_client,
        db_session,
        admin_headers,
        approver_headers,
    )
    order_id = await _create_cod_order(api_client, customer_headers, customer_user, product_id, variant_id, sku)

    forbidden_list = await api_client.get(
        "/api/admin/inventory/outbounds",
        headers=customer_headers,
    )
    assert forbidden_list.status_code == 403, forbidden_list.text

    processing = await api_client.patch(
        f"/api/orders/{order_id}/admin",
        headers=admin_headers,
        json={"status": "PROCESSING", "changed_by": "Admin kiểm thử outbound"},
    )
    assert processing.status_code == 204, processing.text

    document = (
        await db_session.execute(
            text(
                """
                SELECT document_no, status
                FROM inventory_documents
                WHERE order_id = :order_id AND document_type = 'OUTBOUND'
                """
            ),
            {"order_id": order_id},
        )
    ).mappings().one()
    document_no = document["document_no"]
    assert document["status"] == "DRAFT"

    listed = await api_client.get(
        "/api/admin/inventory/outbounds",
        headers=admin_headers,
        params={"search": document_no},
    )
    assert listed.status_code == 200, listed.text
    assert document_no in listed.text

    suggested = await api_client.post(
        f"/api/admin/inventory/outbounds/{document_no}/auto-suggest",
        headers=admin_headers,
    )
    assert suggested.status_code == 200, suggested.text

    suggestion = (
        await db_session.execute(
            text(
                """
                SELECT l.location_id, l.metadata
                FROM inventory_document_lines l
                JOIN inventory_documents d ON d.id = l.document_id
                WHERE d.document_no = :document_no
                """
            ),
            {"document_no": document_no},
        )
    ).mappings().one()
    assert suggestion["location_id"] is not None
    assert suggestion["metadata"]["allocations"]
    assert suggestion["metadata"]["imeis"] == []
    assert suggestion["metadata"]["serialNumbers"] == []
    assert all(allocation["imeis"] == [] for allocation in suggestion["metadata"]["allocations"])
    assert all(allocation["serialNumbers"] == [] for allocation in suggestion["metadata"]["allocations"])

    picked_status = await db_session.scalar(
        text("SELECT status FROM inventory_documents WHERE document_no = :document_no"),
        {"document_no": document_no},
    )
    assert picked_status == "PICKED"

    completed = await api_client.patch(
        f"/api/admin/inventory/outbounds/{document_no}/status",
        headers=admin_headers,
        json={"status": "COMPLETED"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"

    row = (
        await db_session.execute(
            text(
                """
                SELECT
                    d.status AS document_status,
                    o.status AS order_status,
                    p.stock_quantity AS product_stock,
                    pv.stock_quantity AS variant_stock
                FROM inventory_documents d
                JOIN orders o ON o.id = d.order_id
                JOIN product_variants pv ON pv.id = :variant_id
                JOIN products p ON p.id = pv.product_id
                WHERE d.document_no = :document_no
                """
            ),
            {"document_no": document_no, "variant_id": variant_id},
        )
    ).mappings().one()
    assert row["document_status"] == "COMPLETED"
    assert row["order_status"] == "SHIPPED"
    assert row["product_stock"] == 3
    assert row["variant_stock"] == 3

    level_quantity = await db_session.scalar(
        text(
            """
            SELECT COALESCE(SUM(on_hand_quantity), 0)
            FROM inventory_levels
            WHERE variant_id = :variant_id
            """
        ),
        {"variant_id": variant_id},
    )
    assert level_quantity == 3

    repeated = await api_client.patch(
        f"/api/admin/inventory/outbounds/{document_no}/status",
        headers=admin_headers,
        json={"status": "COMPLETED"},
    )
    assert repeated.status_code == 400, repeated.text


@pytest.mark.workflow
async def test_admin_can_cancel_draft_outbound_without_posting_stock(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
    customer_headers,
    customer_user,
):
    product_id, variant_id, sku = await _seed_stocked_variant(
        api_client,
        db_session,
        admin_headers,
        approver_headers,
    )
    order_id = await _create_cod_order(api_client, customer_headers, customer_user, product_id, variant_id, sku)

    processing = await api_client.patch(
        f"/api/orders/{order_id}/admin",
        headers=admin_headers,
        json={"status": "PROCESSING", "changed_by": "Admin kiểm thử outbound"},
    )
    assert processing.status_code == 204, processing.text

    document = (
        await db_session.execute(
            text(
                """
                SELECT document_no, status
                FROM inventory_documents
                WHERE order_id = :order_id AND document_type = 'OUTBOUND'
                """
            ),
            {"order_id": order_id},
        )
    ).mappings().one()
    document_no = document["document_no"]
    assert document["status"] == "DRAFT"

    cancelled = await api_client.patch(
        f"/api/admin/inventory/outbounds/{document_no}/status",
        headers=admin_headers,
        json={"status": "CANCELLED", "cancelReason": "Lập lại phiếu xuất để kiểm thử."},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED"

    row = (
        await db_session.execute(
            text(
                """
                SELECT d.status, d.note, d.cancelled_at, pv.stock_quantity AS variant_stock
                FROM inventory_documents d
                JOIN product_variants pv ON pv.id = :variant_id
                WHERE d.document_no = :document_no
                """
            ),
            {"document_no": document_no, "variant_id": variant_id},
        )
    ).mappings().one()
    assert row["status"] == "CANCELLED"
    assert row["note"] == "Lập lại phiếu xuất để kiểm thử."
    assert row["cancelled_at"] is not None
    assert row["variant_stock"] == 5

    # Thử phát hành lại phiếu xuất đã hủy (chuyển về DRAFT)
    reissue = await api_client.patch(
        f"/api/admin/inventory/outbounds/{document_no}/status",
        headers=admin_headers,
        json={"status": "DRAFT"},
    )
    assert reissue.status_code == 200, reissue.text
    assert reissue.json()["status"] == "DRAFT"

    # Xác minh lại trong db
    status_db = await db_session.scalar(
        text("SELECT status FROM inventory_documents WHERE document_no = :document_no"),
        {"document_no": document_no},
    )
    assert status_db == "DRAFT"
