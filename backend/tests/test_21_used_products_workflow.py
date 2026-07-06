from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_used_device_intake_appraisal_is_separate_from_new_inventory(
    api_client,
    db_session,
    customer_headers,
    customer_user,
    approver_headers,
):
    product_id = uuid4()
    variant_id = uuid4()
    sku = f"USED-{uuid4().hex[:8].upper()}"
    imei = ("35" + str(uuid4().int))[:15]
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, specifications
            )
            VALUES (
                :id, :sku, 'Điện thoại kiểm thử hàng cũ', :slug,
                'PHONE', 'Thương hiệu kiểm thử', 15000000, 14000000,
                0, 'ACTIVE', '{"screen": "6.1 inch"}'::jsonb
            )
            """
        ),
        {"id": product_id, "sku": sku, "slug": f"used-test-{uuid4().hex[:8]}"},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_variants (
                id, product_id, sku, color_name, storage, ram,
                price, sale_price, stock_quantity, is_active
            )
            VALUES (
                :id, :product_id, :sku, 'Đen', '128GB', '8GB',
                15000000, 14000000, 0, TRUE
            )
            """
        ),
        {"id": variant_id, "product_id": product_id, "sku": f"{sku}-BLACK"},
    )
    await db_session.commit()

    created = await api_client.post(
        "/api/admin/used-products/intakes",
        headers=approver_headers,
        json={
            "sourceType": "USER_BUYBACK",
            "sellerName": "Khách hàng kiểm thử",
            "sellerPhone": "0900000000",
            "productId": str(product_id),
            "variantId": str(variant_id),
            "imei": imei,
            "expectedPrice": 8000000,
        },
    )
    assert created.status_code == 201, created.text
    intake_id = created.json()["id"]

    for status_value in ("RECEIVED", "INSPECTING"):
        response = await api_client.patch(
            f"/api/admin/used-products/intakes/{intake_id}/status",
            headers=approver_headers,
            json={"status": status_value},
        )
        assert response.status_code == 200, response.text

    inspected = await api_client.post(
        f"/api/admin/used-products/intakes/{intake_id}/inspections",
        headers=approver_headers,
        json={
            "outcome": "APPRAISED",
            "conditionGrade": "B",
            "conditionScore": 82,
            "batteryHealth": 88,
            "checklist": {
                "screen": True,
                "camera": True,
                "connectivity": True,
                "biometric": True,
                "accountUnlocked": True,
            },
            "repairCostEstimate": 250000,
            "proposedAcquisitionPrice": 7800000,
            "proposedSalePrice": 10500000,
            "note": "Thiết bị đạt điều kiện bán lại.",
        },
    )
    assert inspected.status_code == 201, inspected.text
    assert inspected.json()["status"] == "APPRAISED"

    accepted = await api_client.patch(
        f"/api/admin/used-products/intakes/{intake_id}/status",
        headers=approver_headers,
        json={"status": "ACCEPTED"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["deviceId"]

    devices = await api_client.get(
        "/api/admin/used-products/devices",
        headers=approver_headers,
    )
    assert devices.status_code == 200, devices.text
    device = next(item for item in devices.json() if item["imei"] == imei)
    assert device["locationCode"] == "CU-01-01"
    assert device["conditionGrade"] == "B"
    assert device["originalSnapshot"]["newReferencePrice"] == 14000000.0
    assert device["approvedSalePrice"] == 10500000.0

    listing = await api_client.put(
        f"/api/admin/used-products/devices/{device['id']}/listing",
        headers=approver_headers,
        json={
            "title": "Điện thoại kiểm thử hàng cũ hạng B",
            "description": "Thiết bị đã được thẩm định đầy đủ chức năng và có ảnh thực tế.",
            "highlights": ["Pin 88%", "Bộ nhớ 128GB", "Đã thoát tài khoản"],
            "images": ["/uploads/used-products/test-device.webp"],
            "warrantyMonths": 3,
        },
    )
    assert listing.status_code == 200, listing.text
    listing_id = listing.json()["id"]
    listing_slug = listing.json()["slug"]

    public_before_approval = await api_client.get("/api/storefront/used-products")
    assert public_before_approval.status_code == 200
    assert public_before_approval.json()["total"] == 0

    submitted = await api_client.patch(
        f"/api/admin/used-products/listings/{listing_id}/status",
        headers=approver_headers,
        json={"status": "PENDING_APPROVAL"},
    )
    assert submitted.status_code == 200, submitted.text

    published = await api_client.patch(
        f"/api/admin/used-products/listings/{listing_id}/status",
        headers=approver_headers,
        json={"status": "PUBLISHED"},
    )
    assert published.status_code == 200, published.text

    public_list = await api_client.get("/api/storefront/used-products?grade=B&sort=savings")
    assert public_list.status_code == 200, public_list.text
    assert public_list.json()["total"] == 1
    assert public_list.json()["items"][0]["slug"] == listing_slug

    public_detail = await api_client.get(f"/api/storefront/used-products/{listing_slug}")
    assert public_detail.status_code == 200, public_detail.text
    assert public_detail.json()["maskedImei"].startswith(imei[:4])
    assert "imei" not in public_detail.json()
    assert public_detail.json()["salePrice"] == 10500000.0
    assert public_detail.json()["deviceId"] == device["id"]

    order_payload = {
        "user_id": customer_user["id"],
        "items": [
            {
                "used_device_id": device["id"],
                "product_name": "Điện thoại kiểm thử hàng cũ hạng B",
                "quantity": 1,
                "unit_price": 10500000,
            }
        ],
        "shipping": {
            "recipient_name": "Khách mua hàng cũ",
            "recipient_phone": "0900000099",
            "recipient_email": customer_user["email"],
            "shipping_address": "123 Đường hàng cũ, Thành phố Hồ Chí Minh",
        },
        "payment_method": "COD",
        "idempotency_key": f"used-checkout-{uuid4().hex}",
    }
    first_order = await api_client.post("/api/orders", headers=customer_headers, json=order_payload)
    assert first_order.status_code == 201, first_order.text
    first_order_id = first_order.json()["order_id"]

    reserved_status = await db_session.scalar(
        text("SELECT status FROM used_devices WHERE id = :device_id"),
        {"device_id": device["id"]},
    )
    assert reserved_status == "RESERVED"

    duplicate_order_payload = {**order_payload, "idempotency_key": f"used-checkout-{uuid4().hex}"}
    duplicate_order = await api_client.post("/api/orders", headers=customer_headers, json=duplicate_order_payload)
    assert duplicate_order.status_code == 409, duplicate_order.text

    cancelled = await api_client.patch(
        f"/api/orders/{first_order_id}/admin",
        headers=approver_headers,
        json={"status": "CANCELLED", "cancellation_reason": "Khách đổi ý trong lúc kiểm thử."},
    )
    assert cancelled.status_code == 204, cancelled.text
    released_status = await db_session.scalar(
        text("SELECT status FROM used_devices WHERE id = :device_id"),
        {"device_id": device["id"]},
    )
    assert released_status == "READY_FOR_SALE"

    second_order_payload = {**order_payload, "idempotency_key": f"used-checkout-{uuid4().hex}"}
    second_order = await api_client.post("/api/orders", headers=customer_headers, json=second_order_payload)
    assert second_order.status_code == 201, second_order.text
    second_order_id = second_order.json()["order_id"]

    for next_status in ("PAID", "PROCESSING", "SHIPPED"):
        response = await api_client.patch(
            f"/api/orders/{second_order_id}/status",
            headers=approver_headers,
            json={"status": next_status},
        )
        assert response.status_code == 204, response.text

    sold_status = await db_session.scalar(
        text("SELECT status FROM used_devices WHERE id = :device_id"),
        {"device_id": device["id"]},
    )
    assert sold_status == "SOLD"

    order_item = (
        await db_session.execute(
            text(
                """
                SELECT used_device_id, product_id, quantity, unit_price, warranty_months_snapshot
                FROM order_items
                WHERE order_id = :order_id
                """
            ),
            {"order_id": second_order_id},
        )
    ).mappings().one()
    assert str(order_item["used_device_id"]) == device["id"]
    assert order_item["product_id"] is None
    assert order_item["quantity"] == 1
    assert order_item["warranty_months_snapshot"] == 3

    for next_status in ("RETURNING", "RETURNED"):
        response = await api_client.patch(
            f"/api/orders/{second_order_id}/status",
            headers=approver_headers,
            json={"status": next_status},
        )
        assert response.status_code == 204, response.text

    returned_status = await db_session.scalar(
        text("SELECT status FROM used_devices WHERE id = :device_id"),
        {"device_id": device["id"]},
    )
    assert returned_status == "RETURNED_QC"

    public_after_return = await api_client.get(f"/api/storefront/used-products/{listing_slug}")
    assert public_after_return.status_code == 404

    repairing = await api_client.patch(
        f"/api/admin/used-products/devices/{device['id']}/status",
        headers=approver_headers,
        json={"status": "REPAIRING", "note": "Máy hoàn về cần sửa trước khi QC lại."},
    )
    assert repairing.status_code == 200, repairing.text
    assert repairing.json()["status"] == "REPAIRING"

    back_to_qc = await api_client.patch(
        f"/api/admin/used-products/devices/{device['id']}/status",
        headers=approver_headers,
        json={"status": "RETURNED_QC", "note": "Đã sửa xong, chuyển lại QC."},
    )
    assert back_to_qc.status_code == 200, back_to_qc.text

    qc_passed = await api_client.post(
        f"/api/admin/used-products/devices/{device['id']}/reinspection",
        headers=approver_headers,
        json={
            "outcome": "APPRAISED",
            "conditionGrade": "B",
            "conditionScore": 84,
            "batteryHealth": 86,
            "checklist": {
                "screen": True,
                "camera": True,
                "connectivity": True,
                "biometric": True,
                "accountUnlocked": True,
            },
            "evidence": [{"url": "/uploads/used-products/recheck.webp", "name": "QC lại"}],
            "repairCostEstimate": 350000,
            "proposedAcquisitionPrice": None,
            "proposedSalePrice": 9900000,
            "note": "QC lại đạt, cần duyệt bài đăng lại.",
        },
    )
    assert qc_passed.status_code == 200, qc_passed.text
    assert qc_passed.json()["status"] == "READY_FOR_PRICING"

    device_after_recheck = (
        await db_session.execute(
            text(
                """
                SELECT
                    d.status AS device_status,
                    d.condition_score,
                    d.battery_health,
                    d.refurbishment_cost,
                    d.approved_sale_price,
                    listing.status AS listing_status
                FROM used_devices d
                LEFT JOIN used_device_listings listing ON listing.device_id = d.id
                WHERE d.id = :device_id
                """
            ),
            {"device_id": device["id"]},
        )
    ).mappings().one()
    assert device_after_recheck["device_status"] == "READY_FOR_PRICING"
    assert device_after_recheck["condition_score"] == 84
    assert device_after_recheck["battery_health"] == 86
    assert device_after_recheck["refurbishment_cost"] == 350000
    assert device_after_recheck["approved_sale_price"] == 9900000
    assert device_after_recheck["listing_status"] == "DRAFT"

    public_after_qc_passed = await api_client.get(f"/api/storefront/used-products/{listing_slug}")
    assert public_after_qc_passed.status_code == 404

    history = await api_client.get(
        f"/api/admin/used-products/devices/{device['id']}/history",
        headers=approver_headers,
    )
    assert history.status_code == 200, history.text
    history_payload = history.json()
    assert history_payload["device"]["deviceCode"] == device["deviceCode"]
    entry_types = {item["entryType"] for item in history_payload["items"]}
    assert {"EVENT", "INSPECTION", "PRICE"}.issubset(entry_types)
    assert any(item["title"] == "DEVICE_REINSPECTED" for item in history_payload["items"])
    assert any(
        item["entryType"] == "PRICE" and float(item["approvedSalePrice"]) == 9900000.0
        for item in history_payload["items"]
        if item["approvedSalePrice"] is not None
    )

    new_inventory_quantity = await db_session.scalar(
        text(
            """
            SELECT COALESCE(SUM(on_hand_quantity), 0)
            FROM inventory_levels
            WHERE product_id = :product_id OR variant_id = :variant_id
            """
        ),
        {"product_id": product_id, "variant_id": variant_id},
    )
    assert new_inventory_quantity == 0
