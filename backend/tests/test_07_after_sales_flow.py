from uuid import uuid4

import pytest
from sqlalchemy import text


def _new_test_imei(prefix: str) -> str:
    return f"{prefix}{uuid4().int % 10**13:013d}"


async def _seed_replacement_inventory(db_session, customer_user) -> dict:
    product_id = uuid4()
    order_id = uuid4()
    order_item_id = uuid4()
    old_imei = _new_test_imei("35")
    replacement_imei = _new_test_imei("86")
    old_serial = f"OLD-SERIAL-{uuid4().hex[:10].upper()}"
    replacement_serial = f"NEW-SERIAL-{uuid4().hex[:10].upper()}"
    order_code = f"TEST-REPLACEMENT-{uuid4().hex[:8].upper()}"
    location_id = await db_session.scalar(
        text("SELECT id FROM inventory_locations WHERE code = 'MAIN'")
    )
    assert location_id is not None

    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, stock_quantity,
                status, warranty_period
            )
            VALUES (
                :product_id, :sku, 'Điện thoại thay thế kiểm thử', :slug,
                'PHONE', 'Hãng kiểm thử', 6000000, 1, 'ACTIVE', 12
            )
            """
        ),
        {
            "product_id": product_id,
            "sku": f"TEST-REPLACEMENT-{uuid4().hex[:8].upper()}",
            "slug": f"dien-thoai-thay-the-{uuid4().hex[:8]}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO orders (
                id, user_id, order_code, status, payment_method, payment_status,
                subtotal_amount, discount_amount, shipping_fee, total_amount,
                recipient_name, recipient_phone, shipping_address, completed_at
            )
            VALUES (
                :order_id, :user_id, :order_code, 'COMPLETED', 'COD', 'PAID',
                6000000, 0, 0, 6000000,
                'Khách hàng đổi máy', '0900000006',
                '12 Đường kiểm thử, Thành phố Hồ Chí Minh', NOW()
            )
            """
        ),
        {
            "order_id": order_id,
            "user_id": customer_user["id"],
            "order_code": order_code,
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO order_items (
                id, order_id, product_id, product_name, quantity,
                unit_price, total_price, warranty_months_snapshot
            )
            VALUES (
                :order_item_id, :order_id, :product_id,
                'Điện thoại thay thế kiểm thử', 1, 6000000, 6000000, 12
            )
            """
        ),
        {
            "order_item_id": order_item_id,
            "order_id": order_id,
            "product_id": product_id,
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_levels (
                product_id, location_id, on_hand_quantity, average_unit_cost
            )
            VALUES (:product_id, :location_id, 1, 4500000)
            """
        ),
        {"product_id": product_id, "location_id": location_id},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_imeis (
                id, product_id, imei, status, sold_order_id, sold_at
            )
            VALUES (:id, :product_id, :imei, 'SOLD', :order_id, NOW())
            """
        ),
        {
            "id": uuid4(),
            "product_id": product_id,
            "imei": old_imei,
            "order_id": order_id,
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_imeis (
                id, product_id, imei, status, location_id
            )
            VALUES (:id, :product_id, :imei, 'IN_STOCK', :location_id)
            """
        ),
        {
            "id": uuid4(),
            "product_id": product_id,
            "imei": replacement_imei,
            "location_id": location_id,
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (
                id, product_id, serial_number, status, sold_at, service_payload
            )
            VALUES (
                :id, :product_id, :serial_number, 'SOLD', NOW(),
                jsonb_build_object('soldOrderId', CAST(CAST(:order_id AS UUID) AS TEXT))
            )
            """
        ),
        {
            "id": uuid4(),
            "product_id": product_id,
            "serial_number": old_serial,
            "order_id": order_id,
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (
                id, product_id, serial_number, status, location_id
            )
            VALUES (
                :id, :product_id, :serial_number, 'IN_STOCK', :location_id
            )
            """
        ),
        {
            "id": uuid4(),
            "product_id": product_id,
            "serial_number": replacement_serial,
            "location_id": location_id,
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_identifier_pairs (
                id, product_id, imei1, serial_number, source_reference
            )
            VALUES
                (:old_pair_id, :product_id, :old_imei, :old_serial, :source_reference),
                (:new_pair_id, :product_id, :replacement_imei, :replacement_serial, :source_reference)
            """
        ),
        {
            "old_pair_id": uuid4(),
            "new_pair_id": uuid4(),
            "product_id": product_id,
            "old_imei": old_imei,
            "old_serial": old_serial,
            "replacement_imei": replacement_imei,
            "replacement_serial": replacement_serial,
            "source_reference": order_code,
        },
    )
    await db_session.commit()
    return {
        "product_id": product_id,
        "order_id": order_id,
        "order_item_id": order_item_id,
        "order_code": order_code,
        "location_id": location_id,
        "old_imei": old_imei,
        "replacement_imei": replacement_imei,
        "old_serial": old_serial,
        "replacement_serial": replacement_serial,
    }


@pytest.mark.workflow
async def test_completed_order_return_request_and_customer_cancellation(
    api_client,
    db_session,
    customer_user,
    customer_headers,
    admin_headers,
):
    product_id = uuid4()
    order_id = uuid4()
    order_item_id = uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, stock_quantity,
                status, warranty_period
            )
            VALUES (
                :product_id, :sku, 'Sản phẩm hậu mãi kiểm thử', :slug,
                'ACCESSORY', 'Hãng kiểm thử', 1000000, 0, 'ACTIVE', 12
            )
            """
        ),
        {
            "product_id": product_id,
            "sku": f"TEST-AS-{uuid4().hex[:8].upper()}",
            "slug": f"san-pham-hau-mai-{uuid4().hex[:8]}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO orders (
                id, user_id, order_code, status, payment_method, payment_status,
                subtotal_amount, discount_amount, shipping_fee, total_amount,
                recipient_name, recipient_phone, shipping_address, completed_at
            )
            VALUES (
                :order_id, :user_id, :order_code, 'COMPLETED', 'COD', 'PAID',
                1000000, 0, 0, 1000000,
                'Khách hàng kiểm thử', '0900000002',
                '123 Đường kiểm thử, Thành phố Hồ Chí Minh', NOW()
            )
            """
        ),
        {
            "order_id": order_id,
            "user_id": customer_user["id"],
            "order_code": f"TEST-ORDER-{uuid4().hex[:8].upper()}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO order_items (
                id, order_id, product_id, product_name, quantity, unit_price, total_price
            )
            VALUES (
                :order_item_id, :order_id, :product_id,
                'Sản phẩm hậu mãi kiểm thử', 1, 1000000, 1000000
            )
            """
        ),
        {
            "product_id": product_id,
            "order_id": order_id,
            "order_item_id": order_item_id,
        },
    )
    await db_session.commit()

    created = await api_client.post(
        "/api/me/returns",
        headers=customer_headers,
        json={
            "order_id": str(order_id),
            "reason": "Sản phẩm có lỗi chức năng cần được kiểm tra.",
            "items": [{"order_item_id": str(order_item_id), "quantity": 1}],
        },
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]

    stored_status = await db_session.scalar(
        text("SELECT status FROM return_requests WHERE id = :request_id"),
        {"request_id": request_id},
    )
    assert stored_status == "SUBMITTED"

    customer_list = await api_client.get("/api/me/returns", headers=customer_headers)
    assert customer_list.status_code == 200, customer_list.text
    assert request_id in customer_list.text

    attachment_id = uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO after_sales_attachments (
                id, reference_type, reference_id, uploaded_by, original_name,
                storage_key, content_type, size_bytes, checksum_sha256
            )
            VALUES (
                :attachment_id, 'RETURN', :request_id, :user_id, 'man-hinh-loi.png',
                :storage_key, 'image/png', 128, :checksum
            )
            """
        ),
        {
            "attachment_id": attachment_id,
            "request_id": request_id,
            "user_id": customer_user["id"],
            "storage_key": f"uploads/after-sales/return/{request_id}/man-hinh-loi.png",
            "checksum": "0" * 64,
        },
    )
    await db_session.commit()

    admin_list = await api_client.get(
        "/api/admin/after-sales/returns",
        headers=admin_headers,
    )
    assert admin_list.status_code == 200, admin_list.text
    assert request_id in admin_list.text
    admin_request = next(item for item in admin_list.json()["items"] if item["id"] == request_id)
    assert admin_request["attachments"][0]["originalName"] == "man-hinh-loi.png"
    assert admin_request["attachments"][0]["url"] == f"/uploads/after-sales/return/{request_id}/man-hinh-loi.png"

    rejected_without_note = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={"status": "REJECTED"},
    )
    assert rejected_without_note.status_code == 400, rejected_without_note.text
    assert "lý do" in rejected_without_note.text

    cancelled = await api_client.post(
        f"/api/me/returns/{request_id}/cancel",
        headers=customer_headers,
    )
    assert cancelled.status_code == 204, cancelled.text
    final_status = await db_session.scalar(
        text("SELECT status FROM return_requests WHERE id = :request_id"),
        {"request_id": request_id},
    )
    assert final_status == "CANCELLED"


@pytest.mark.workflow
async def test_admin_warranty_repair_details_are_saved_and_listed(
    api_client,
    db_session,
    customer_user,
    customer_headers,
    admin_headers,
):
    product_id = uuid4()
    order_id = uuid4()
    order_item_id = uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, stock_quantity,
                status, warranty_period
            )
            VALUES (
                :product_id, :sku, 'Điện thoại bảo hành kiểm thử', :slug,
                'PHONE', 'Hãng kiểm thử', 5000000, 0, 'ACTIVE', 12
            )
            """
        ),
        {
            "product_id": product_id,
            "sku": f"TEST-WR-{uuid4().hex[:8].upper()}",
            "slug": f"dien-thoai-bao-hanh-{uuid4().hex[:8]}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO orders (
                id, user_id, order_code, status, payment_method, payment_status,
                subtotal_amount, discount_amount, shipping_fee, total_amount,
                recipient_name, recipient_phone, shipping_address, completed_at
            )
            VALUES (
                :order_id, :user_id, :order_code, 'COMPLETED', 'COD', 'PAID',
                5000000, 0, 0, 5000000,
                'Khách hàng bảo hành', '0900000003',
                '456 Đường kiểm thử, Thành phố Hồ Chí Minh', NOW()
            )
            """
        ),
        {
            "order_id": order_id,
            "user_id": customer_user["id"],
            "order_code": f"TEST-WARRANTY-{uuid4().hex[:8].upper()}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO order_items (
                id, order_id, product_id, product_name, quantity, unit_price, total_price
            )
            VALUES (
                :order_item_id, :order_id, :product_id,
                'Điện thoại bảo hành kiểm thử', 1, 5000000, 5000000
            )
            """
        ),
        {
            "product_id": product_id,
            "order_id": order_id,
            "order_item_id": order_item_id,
        },
    )
    await db_session.commit()

    created = await api_client.post(
        "/api/me/warranties",
        headers=customer_headers,
        json={
            "order_id": str(order_id),
            "reason": "Máy mất nguồn cần trung tâm kỹ thuật kiểm tra bảo hành.",
            "items": [{"order_item_id": str(order_item_id), "quantity": 1}],
        },
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]

    for status in ["RECEIVED", "QC_IN_PROGRESS"]:
        updated = await api_client.patch(
            f"/api/admin/after-sales/warranties/{request_id}/status",
            headers=admin_headers,
            json={"status": status, "note": f"Chuyển sang {status}"},
        )
        assert updated.status_code == 200, updated.text

    inspected = await api_client.post(
        f"/api/admin/after-sales/warranties/{request_id}/inspection",
        headers=admin_headers,
        json={
            "result": "ACCEPT_REPAIR",
            "qc_note": "Thiết bị lỗi nguồn và đủ điều kiện bảo hành.",
            "customer_fault": False,
        },
    )
    assert inspected.status_code == 200, inspected.text

    repaired = await api_client.patch(
        f"/api/admin/after-sales/warranties/{request_id}/status",
        headers=admin_headers,
        json={
            "status": "REPAIRING",
            "note": "Kỹ thuật bắt đầu sửa chữa.",
            "repair_diagnosis": "Mất nguồn do lỗi IC sạc.",
            "repair_action": "Thay IC sạc và kiểm tra lại nguồn.",
            "repair_parts": "IC sạc",
            "repair_cost": 350000,
        },
    )
    assert repaired.status_code == 200, repaired.text

    metadata = await db_session.scalar(
        text(
            """
            SELECT metadata
            FROM after_sales_events
            WHERE reference_type = 'WARRANTY'
              AND reference_id = :request_id
              AND new_status = 'REPAIRING'
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"request_id": request_id},
    )
    assert metadata["repair"]["diagnosis"] == "Mất nguồn do lỗi IC sạc."
    assert metadata["repair"]["parts"] == "IC sạc"
    assert metadata["repair"]["cost"] == 350000

    admin_list = await api_client.get("/api/admin/after-sales/warranties", headers=admin_headers)
    assert admin_list.status_code == 200, admin_list.text
    listed = next(item for item in admin_list.json()["items"] if item["id"] == request_id)
    assert listed["repairSummary"]["diagnosis"] == "Mất nguồn do lỗi IC sạc."
    assert listed["repairSummary"]["action"] == "Thay IC sạc và kiểm tra lại nguồn."

    events = await api_client.get(
        f"/api/admin/after-sales/warranties/{request_id}/events",
        headers=admin_headers,
    )
    assert events.status_code == 200, events.text
    repair_events = [event for event in events.json() if event["newStatus"] == "REPAIRING"]
    assert repair_events
    assert repair_events[-1]["metadata"]["repair"]["parts"] == "IC sạc"

    manual_note = await api_client.post(
        f"/api/admin/after-sales/warranties/{request_id}/events",
        headers=admin_headers,
        json={"note": "Đã gọi khách xác nhận lịch trả máy vào chiều mai."},
    )
    assert manual_note.status_code == 201, manual_note.text

    updated_events = await api_client.get(
        f"/api/admin/after-sales/warranties/{request_id}/events",
        headers=admin_headers,
    )
    assert updated_events.status_code == 200, updated_events.text
    manual_events = [event for event in updated_events.json() if event["metadata"].get("manualNote")]
    assert manual_events
    assert manual_events[-1]["note"] == "Đã gọi khách xác nhận lịch trả máy vào chiều mai."


@pytest.mark.workflow
async def test_warranty_request_uses_order_item_warranty_snapshot(
    api_client,
    db_session,
    customer_user,
    customer_headers,
):
    async def create_completed_order_with_product_warranty(warranty_months: int) -> tuple[str, str, str]:
        product_id = uuid4()
        await db_session.execute(
            text(
                """
                INSERT INTO products (
                    id, sku, name, slug, category, brand, price, sale_price,
                    stock_quantity, status, warranty_period
                )
                VALUES (
                    :product_id, :sku, :name, :slug,
                    'PHONE', 'Hãng kiểm thử', 2000000, 2000000,
                    5, 'ACTIVE', :warranty_months
                )
                """
            ),
            {
                "product_id": product_id,
                "sku": f"TEST-WARRANTY-SNAPSHOT-{uuid4().hex[:8].upper()}",
                "name": f"Sản phẩm snapshot bảo hành {warranty_months} tháng",
                "slug": f"san-pham-snapshot-bao-hanh-{uuid4().hex[:8]}",
                "warranty_months": warranty_months,
            },
        )
        await db_session.commit()

        created = await api_client.post(
            "/api/orders",
            headers=customer_headers,
            json={
                "user_id": customer_user["id"],
                "items": [
                    {
                        "product_id": str(product_id),
                        "product_name": f"Sản phẩm snapshot bảo hành {warranty_months} tháng",
                        "quantity": 1,
                        "unit_price": 2000000,
                    }
                ],
                "shipping": {
                    "recipient_name": "Khách hàng kiểm thử",
                    "recipient_phone": "0900000003",
                    "recipient_email": customer_user["email"],
                    "shipping_address": "123 Đường kiểm thử, Thành phố Hồ Chí Minh",
                },
                "payment_method": "COD",
                "idempotency_key": f"test-warranty-snapshot-{uuid4().hex}",
            },
        )
        assert created.status_code == 201, created.text
        order_id = created.json()["order_id"]
        order_item = (
            await db_session.execute(
                text(
                    """
                    SELECT id, warranty_months_snapshot
                    FROM order_items
                    WHERE order_id = :order_id
                    """
                ),
                {"order_id": order_id},
            )
        ).mappings().one()
        assert order_item["warranty_months_snapshot"] == warranty_months
        await db_session.execute(
            text(
                """
                UPDATE orders
                SET status = 'COMPLETED',
                    payment_status = 'PAID',
                    completed_at = NOW()
                WHERE id = :order_id
                """
            ),
            {"order_id": order_id},
        )
        await db_session.commit()
        return str(product_id), order_id, str(order_item["id"])

    product_id, order_id, order_item_id = await create_completed_order_with_product_warranty(12)
    await db_session.execute(
        text("UPDATE products SET warranty_period = 0 WHERE id = :product_id"),
        {"product_id": product_id},
    )
    await db_session.commit()

    created_warranty = await api_client.post(
        "/api/me/warranties",
        headers=customer_headers,
        json={
            "order_id": order_id,
            "reason": "Máy lỗi nguồn trong thời hạn bảo hành snapshot.",
            "items": [{"order_item_id": order_item_id, "quantity": 1}],
        },
    )
    assert created_warranty.status_code == 201, created_warranty.text

    product_without_warranty_id, order_without_warranty_id, item_without_warranty_id = await create_completed_order_with_product_warranty(0)
    await db_session.execute(
        text("UPDATE products SET warranty_period = 12 WHERE id = :product_id"),
        {"product_id": product_without_warranty_id},
    )
    await db_session.commit()

    rejected_warranty = await api_client.post(
        "/api/me/warranties",
        headers=customer_headers,
        json={
            "order_id": order_without_warranty_id,
            "reason": "Không được hưởng chính sách bảo hành được bật sau thời điểm mua.",
            "items": [{"order_item_id": item_without_warranty_id, "quantity": 1}],
        },
    )
    assert rejected_warranty.status_code == 400, rejected_warranty.text
    assert "không hỗ trợ chế độ bảo hành" in rejected_warranty.text


@pytest.mark.workflow
async def test_used_device_warranty_request_uses_order_item_snapshot(
    api_client,
    db_session,
    customer_user,
    customer_headers,
):
    product_id = uuid4()
    intake_id = uuid4()
    device_id = uuid4()
    order_id = uuid4()
    order_item_id = uuid4()
    location_id = await db_session.scalar(text("SELECT id FROM inventory_locations WHERE code = 'CU-01-01' LIMIT 1"))
    assert location_id is not None

    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, warranty_period
            )
            VALUES (
                :product_id, :sku, 'Sản phẩm gốc hàng cũ', :slug,
                'PHONE', 'Hãng kiểm thử', 5000000, 5000000,
                0, 'ACTIVE', 0
            )
            """
        ),
        {
            "product_id": product_id,
            "sku": f"TEST-USED-WARRANTY-{uuid4().hex[:8].upper()}",
            "slug": f"san-pham-goc-hang-cu-{uuid4().hex[:8]}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO used_device_intake_requests (
                id, request_code, source_type, seller_name, seller_phone,
                product_id, imei, status
            )
            VALUES (
                :intake_id, :request_code, 'USER_BUYBACK', 'Khách bán máy cũ',
                '0900000000', :product_id, :imei, 'ACCEPTED'
            )
            """
        ),
        {
            "intake_id": intake_id,
            "request_code": f"USED-WARRANTY-{uuid4().hex[:8].upper()}",
            "product_id": product_id,
            "imei": ("86" + str(uuid4().int))[:15],
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO used_devices (
                id, device_code, intake_request_id, product_id, location_id,
                imei, condition_grade, condition_score, status,
                approved_sale_price, warranty_months
            )
            VALUES (
                :device_id, :device_code, :intake_id, :product_id, :location_id,
                :imei, 'B', 82, 'SOLD', 4500000, 3
            )
            """
        ),
        {
            "device_id": device_id,
            "device_code": f"UDW-{uuid4().hex[:8].upper()}",
            "intake_id": intake_id,
            "product_id": product_id,
            "location_id": location_id,
            "imei": ("87" + str(uuid4().int))[:15],
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO orders (
                id, user_id, order_code, status, payment_method, payment_status,
                subtotal_amount, discount_amount, shipping_fee, total_amount,
                recipient_name, recipient_phone, recipient_email, shipping_address,
                completed_at
            )
            VALUES (
                :order_id, :user_id, :order_code, 'COMPLETED', 'COD', 'PAID',
                4500000, 0, 0, 4500000,
                'Khách mua máy cũ', '0900000003', :email,
                '123 Đường kiểm thử, Thành phố Hồ Chí Minh', NOW()
            )
            """
        ),
        {
            "order_id": order_id,
            "user_id": customer_user["id"],
            "order_code": f"USEDWARRANTY{uuid4().hex[:8].upper()}",
            "email": customer_user["email"],
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO order_items (
                id, order_id, used_device_id, product_name, quantity,
                unit_price, total_price, warranty_months_snapshot
            )
            VALUES (
                :order_item_id, :order_id, :device_id, 'Máy cũ bảo hành snapshot',
                1, 4500000, 4500000, 3
            )
            """
        ),
        {"order_item_id": order_item_id, "order_id": order_id, "device_id": device_id},
    )
    await db_session.commit()

    created = await api_client.post(
        "/api/me/warranties",
        headers=customer_headers,
        json={
            "order_id": str(order_id),
            "reason": "Máy cũ lỗi trong thời hạn bảo hành 3 tháng.",
            "items": [{"order_item_id": str(order_item_id), "quantity": 1}],
        },
    )
    assert created.status_code == 201, created.text


@pytest.mark.workflow
async def test_return_refund_path_does_not_require_replacement_stock(
    api_client,
    db_session,
    customer_user,
    customer_headers,
    admin_headers,
):
    product_id = uuid4()
    order_id = uuid4()
    order_item_id = uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, stock_quantity,
                status, warranty_period
            )
            VALUES (
                :product_id, :sku, 'Sản phẩm hoàn tiền kiểm thử', :slug,
                'ACCESSORY', 'Hãng kiểm thử', 1200000, 0, 'ACTIVE', 12
            )
            """
        ),
        {
            "product_id": product_id,
            "sku": f"TEST-RF-{uuid4().hex[:8].upper()}",
            "slug": f"san-pham-hoan-tien-{uuid4().hex[:8]}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO orders (
                id, user_id, order_code, status, payment_method, payment_status,
                subtotal_amount, discount_amount, shipping_fee, total_amount,
                recipient_name, recipient_phone, shipping_address, completed_at
            )
            VALUES (
                :order_id, :user_id, :order_code, 'COMPLETED', 'COD', 'PAID',
                1200000, 0, 0, 1200000,
                'Khách hàng hoàn tiền', '0900000005',
                '789 Đường kiểm thử, Thành phố Hồ Chí Minh', NOW()
            )
            """
        ),
        {
            "order_id": order_id,
            "user_id": customer_user["id"],
            "order_code": f"TEST-REFUND-{uuid4().hex[:8].upper()}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO order_items (
                id, order_id, product_id, product_name, quantity, unit_price, total_price
            )
            VALUES (
                :order_item_id, :order_id, :product_id,
                'Sản phẩm hoàn tiền kiểm thử', 1, 1200000, 1200000
            )
            """
        ),
        {
            "product_id": product_id,
            "order_id": order_id,
            "order_item_id": order_item_id,
        },
    )
    await db_session.commit()

    created = await api_client.post(
        "/api/me/returns",
        headers=customer_headers,
        json={
            "order_id": str(order_id),
            "reason": "Sản phẩm lỗi và khách muốn hoàn tiền sau kiểm tra.",
            "items": [{"order_item_id": str(order_item_id), "quantity": 1}],
        },
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]

    for status_value in ("RECEIVED", "QC_IN_PROGRESS"):
        updated = await api_client.patch(
            f"/api/admin/after-sales/returns/{request_id}/status",
            headers=admin_headers,
            json={"status": status_value, "note": f"Chuyển sang {status_value}"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["status"] == status_value

    inspected = await api_client.post(
        f"/api/admin/after-sales/returns/{request_id}/inspection",
        headers=admin_headers,
        json={
            "result": "APPROVE_REFUND",
            "qc_note": "QC xác nhận lỗi đủ điều kiện hoàn tiền, không cấp hàng thay thế.",
            "customer_fault": False,
            "depreciation_fee": 0,
        },
    )
    assert inspected.status_code == 200, inspected.text
    assert inspected.json()["status"] == "QC_APPROVED"
    assert inspected.json()["resolutionType"] == "REFUND"

    allocation_after_inspection = await db_session.scalar(
        text("SELECT COUNT(*) FROM after_sales_allocations WHERE reference_id = :request_id"),
        {"request_id": request_id},
    )
    assert allocation_after_inspection == 0

    refund_processing = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={"status": "REFUND_PROCESSING", "note": "Xử lý hoàn tiền."},
    )
    assert refund_processing.status_code == 200, refund_processing.text
    assert refund_processing.json()["status"] == "REFUND_PROCESSING"

    allocation_count = await db_session.scalar(
        text("SELECT COUNT(*) FROM after_sales_allocations WHERE reference_id = :request_id"),
        {"request_id": request_id},
    )
    resolution_type = await db_session.scalar(
        text("SELECT resolution_type FROM return_requests WHERE id = :request_id"),
        {"request_id": request_id},
    )
    assert allocation_count == 0
    assert resolution_type == "REFUND"

    missing_ref = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={"status": "COMPLETED", "note": "Thiếu chứng từ hoàn tiền."},
    )
    assert missing_ref.status_code == 400, missing_ref.text

    completed = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={
            "status": "COMPLETED",
            "note": "Đã hoàn tiền cho khách hàng.",
            "refund_transaction_ref": "REF-TEST-001",
            "refund_proof_url": "https://example.com/refund-proof.pdf",
            "refund_note": "Hoàn tiền qua chuyển khoản kiểm thử.",
        },
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"

    refund_transaction = (
        await db_session.execute(
            text(
                """
                SELECT status, transaction_ref, completed_at, metadata
                FROM refund_transactions
                WHERE return_request_id = :request_id
                """
            ),
            {"request_id": request_id},
        )
    ).mappings().one()
    assert refund_transaction["status"] == "COMPLETED"
    assert refund_transaction["transaction_ref"] == "REF-TEST-001"
    assert refund_transaction["completed_at"] is not None
    assert refund_transaction["metadata"]["proofUrl"] == "https://example.com/refund-proof.pdf"
    assert refund_transaction["metadata"]["processedNote"] == "Hoàn tiền qua chuyển khoản kiểm thử."


@pytest.mark.workflow
async def test_return_exchange_creates_linked_inventory_outbound(
    api_client,
    db_session,
    customer_user,
    customer_headers,
    admin_headers,
):
    seeded = await _seed_replacement_inventory(db_session, customer_user)
    created = await api_client.post(
        "/api/me/returns",
        headers=customer_headers,
        json={
            "order_id": str(seeded["order_id"]),
            "reason": "Điện thoại lỗi phần cứng cần đổi thiết bị tương đương.",
            "items": [
                {
                    "order_item_id": str(seeded["order_item_id"]),
                    "quantity": 1,
                    "imei": seeded["old_imei"],
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]

    for status_value in ("RECEIVED", "QC_IN_PROGRESS"):
        updated = await api_client.patch(
            f"/api/admin/after-sales/returns/{request_id}/status",
            headers=admin_headers,
            json={"status": status_value, "note": f"Chuyển sang {status_value}"},
        )
        assert updated.status_code == 200, updated.text

    inspected = await api_client.post(
        f"/api/admin/after-sales/returns/{request_id}/inspection",
        headers=admin_headers,
        json={
            "result": "APPROVE_EXCHANGE",
            "qc_note": "QC xác nhận lỗi đủ điều kiện đổi thiết bị tương đương.",
        },
    )
    assert inspected.status_code == 200, inspected.text
    assert inspected.json()["status"] == "QC_APPROVED"
    allocation_after_qc = await db_session.scalar(
        text("SELECT COUNT(*) FROM after_sales_allocations WHERE reference_id = :request_id"),
        {"request_id": request_id},
    )
    assert allocation_after_qc == 0

    processing = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={"status": "EXCHANGE_PROCESSING", "note": "Bắt đầu chuẩn bị máy đổi."},
    )
    assert processing.status_code == 200, processing.text
    assert processing.json()["status"] == "EXCHANGE_PROCESSING"

    missing_imei = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={"status": "COMPLETED", "note": "Chưa quét IMEI thay thế."},
    )
    assert missing_imei.status_code == 400, missing_imei.text

    completed = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={
            "status": "COMPLETED",
            "note": "Đã cấp máy đổi cho khách hàng.",
            "replacement_imei": seeded["replacement_imei"],
        },
    )
    assert completed.status_code == 200, completed.text

    outbound = (
        await db_session.execute(
            text(
                """
                SELECT d.document_no, d.status, d.reason, d.order_id,
                       d.return_request_id, d.warranty_request_id, d.metadata,
                       l.unit_cost, l.metadata AS line_metadata
                FROM inventory_documents d
                JOIN inventory_document_lines l ON l.document_id = d.id
                WHERE d.return_request_id = :request_id
                """
            ),
            {"request_id": request_id},
        )
    ).mappings().one()
    assert outbound["status"] == "COMPLETED"
    assert outbound["reason"] == "AFTER_SALES_REPLACEMENT"
    assert str(outbound["order_id"]) == str(seeded["order_id"])
    assert str(outbound["return_request_id"]) == request_id
    assert outbound["warranty_request_id"] is None
    assert outbound["metadata"]["stockMutationSkipped"] is True
    assert outbound["line_metadata"]["imeis"] == [seeded["replacement_imei"]]
    assert float(outbound["unit_cost"]) == 4500000

    stock = await db_session.scalar(
        text(
            """
            SELECT on_hand_quantity
            FROM inventory_levels
            WHERE product_id = :product_id AND location_id = :location_id
            """
        ),
        {"product_id": seeded["product_id"], "location_id": seeded["location_id"]},
    )
    allocation_status = await db_session.scalar(
        text(
            """
            SELECT status
            FROM after_sales_allocations
            WHERE reference_type = 'RETURN' AND reference_id = :request_id
            """
        ),
        {"request_id": request_id},
    )
    assert stock == 0
    assert allocation_status == "CONSUMED"

    listed = await api_client.get(
        f"/api/admin/inventory/outbounds?search={outbound['metadata']['requestCode']}",
        headers=admin_headers,
    )
    assert listed.status_code == 200, listed.text
    linked = next(item for item in listed.json() if item["document_no"] == outbound["document_no"])
    assert linked["afterSalesType"] == "RETURN"
    assert linked["afterSalesRequestCode"]


@pytest.mark.workflow
async def test_warranty_replacement_assigns_imei_before_ready_to_return(
    api_client,
    db_session,
    customer_user,
    customer_headers,
    admin_headers,
):
    seeded = await _seed_replacement_inventory(db_session, customer_user)
    created = await api_client.post(
        "/api/me/warranties",
        headers=customer_headers,
        json={
            "order_id": str(seeded["order_id"]),
            "reason": "Điện thoại lỗi nguồn trong thời hạn bảo hành và cần thay máy.",
            "items": [
                {
                    "order_item_id": str(seeded["order_item_id"]),
                    "quantity": 1,
                    "imei": seeded["old_imei"],
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]

    for status_value in ("RECEIVED", "QC_IN_PROGRESS"):
        updated = await api_client.patch(
            f"/api/admin/after-sales/warranties/{request_id}/status",
            headers=admin_headers,
            json={"status": status_value, "note": f"Chuyển sang {status_value}"},
        )
        assert updated.status_code == 200, updated.text

    inspected = await api_client.post(
        f"/api/admin/after-sales/warranties/{request_id}/inspection",
        headers=admin_headers,
        json={
            "result": "APPROVE_REPLACEMENT",
            "qc_note": "QC xác nhận thiết bị đủ điều kiện thay máy bảo hành.",
        },
    )
    assert inspected.status_code == 200, inspected.text
    assert inspected.json()["status"] == "REPLACEMENT_APPROVED"

    processing = await api_client.patch(
        f"/api/admin/after-sales/warranties/{request_id}/status",
        headers=admin_headers,
        json={"status": "REPLACEMENT_PROCESSING", "note": "Chuẩn bị máy bảo hành thay thế."},
    )
    assert processing.status_code == 200, processing.text

    missing_imei = await api_client.patch(
        f"/api/admin/after-sales/warranties/{request_id}/status",
        headers=admin_headers,
        json={"status": "READY_TO_RETURN", "note": "Chưa quét IMEI thay thế."},
    )
    assert missing_imei.status_code == 400, missing_imei.text

    ready = await api_client.patch(
        f"/api/admin/after-sales/warranties/{request_id}/status",
        headers=admin_headers,
        json={
            "status": "READY_TO_RETURN",
            "note": "Máy thay thế đã sẵn sàng trả khách.",
            "replacement_imei": seeded["replacement_imei"],
        },
    )
    assert ready.status_code == 200, ready.text
    assert ready.json()["status"] == "READY_TO_RETURN"

    completed = await api_client.patch(
        f"/api/admin/after-sales/warranties/{request_id}/status",
        headers=admin_headers,
        json={"status": "COMPLETED", "note": "Khách hàng đã nhận máy thay thế."},
    )
    assert completed.status_code == 200, completed.text

    outbound_count = await db_session.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM inventory_documents
            WHERE warranty_request_id = :request_id
              AND document_type = 'OUTBOUND'
              AND status <> 'CANCELLED'
            """
        ),
        {"request_id": request_id},
    )
    replacement_on_item = await db_session.scalar(
        text(
            """
            SELECT replacement_imei
            FROM warranty_request_items
            WHERE request_id = :request_id
            """
        ),
        {"request_id": request_id},
    )
    stock = await db_session.scalar(
        text(
            """
            SELECT on_hand_quantity
            FROM inventory_levels
            WHERE product_id = :product_id AND location_id = :location_id
            """
        ),
        {"product_id": seeded["product_id"], "location_id": seeded["location_id"]},
    )
    assert outbound_count == 1
    assert replacement_on_item == seeded["replacement_imei"]
    assert stock == 0


@pytest.mark.workflow
async def test_return_exchange_supports_multiple_items_and_serial_only_product(
    api_client,
    db_session,
    customer_user,
    customer_headers,
    admin_headers,
):
    seeded = await _seed_replacement_inventory(db_session, customer_user)
    serial_product_id = uuid4()
    serial_order_item_id = uuid4()
    old_serial = f"OLD-ONLY-{uuid4().hex[:10].upper()}"
    replacement_serial = f"NEW-ONLY-{uuid4().hex[:10].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, stock_quantity,
                status, warranty_period
            )
            VALUES (
                :product_id, :sku, 'Thiết bị serial kiểm thử', :slug,
                'ACCESSORY', 'Hãng kiểm thử', 2000000, 1, 'ACTIVE', 12
            )
            """
        ),
        {
            "product_id": serial_product_id,
            "sku": f"TEST-SERIAL-REPLACEMENT-{uuid4().hex[:8].upper()}",
            "slug": f"thiet-bi-serial-thay-the-{uuid4().hex[:8]}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO order_items (
                id, order_id, product_id, product_name, quantity,
                unit_price, total_price, warranty_months_snapshot
            )
            VALUES (
                :order_item_id, :order_id, :product_id,
                'Thiết bị serial kiểm thử', 1, 2000000, 2000000, 12
            )
            """
        ),
        {
            "order_item_id": serial_order_item_id,
            "order_id": seeded["order_id"],
            "product_id": serial_product_id,
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_levels (
                product_id, location_id, on_hand_quantity, average_unit_cost
            )
            VALUES (:product_id, :location_id, 1, 1500000)
            """
        ),
        {"product_id": serial_product_id, "location_id": seeded["location_id"]},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (
                id, product_id, serial_number, status, sold_at, service_payload
            )
            VALUES (
                :id, :product_id, :serial_number, 'SOLD', NOW(),
                jsonb_build_object('soldOrderId', CAST(CAST(:order_id AS UUID) AS TEXT))
            )
            """
        ),
        {
            "id": uuid4(),
            "product_id": serial_product_id,
            "serial_number": old_serial,
            "order_id": seeded["order_id"],
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (
                id, product_id, serial_number, status, location_id
            )
            VALUES (:id, :product_id, :serial_number, 'IN_STOCK', :location_id)
            """
        ),
        {
            "id": uuid4(),
            "product_id": serial_product_id,
            "serial_number": replacement_serial,
            "location_id": seeded["location_id"],
        },
    )
    await db_session.commit()

    created = await api_client.post(
        "/api/me/returns",
        headers=customer_headers,
        json={
            "order_id": str(seeded["order_id"]),
            "reason": "Hai thiết bị lỗi cần được đổi đồng thời sau khi kiểm tra.",
            "items": [
                {
                    "order_item_id": str(seeded["order_item_id"]),
                    "quantity": 1,
                    "imei": seeded["old_imei"],
                },
                {
                    "order_item_id": str(serial_order_item_id),
                    "quantity": 1,
                    "serial_number": old_serial,
                },
            ],
        },
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]

    for status_value in ("RECEIVED", "QC_IN_PROGRESS"):
        updated = await api_client.patch(
            f"/api/admin/after-sales/returns/{request_id}/status",
            headers=admin_headers,
            json={"status": status_value, "note": f"Chuyển sang {status_value}"},
        )
        assert updated.status_code == 200, updated.text
    inspected = await api_client.post(
        f"/api/admin/after-sales/returns/{request_id}/inspection",
        headers=admin_headers,
        json={
            "result": "APPROVE_EXCHANGE",
            "qc_note": "QC xác nhận cả hai thiết bị đủ điều kiện đổi.",
        },
    )
    assert inspected.status_code == 200, inspected.text
    processing = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={"status": "EXCHANGE_PROCESSING", "note": "Chuẩn bị hai thiết bị thay thế."},
    )
    assert processing.status_code == 200, processing.text

    request_item_rows = (
        await db_session.execute(
            text(
                """
                SELECT id, order_item_id
                FROM return_request_items
                WHERE request_id = :request_id
                """
            ),
            {"request_id": request_id},
        )
    ).mappings().all()
    request_item_ids = {
        str(row["order_item_id"]): str(row["id"])
        for row in request_item_rows
    }

    incomplete = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={
            "status": "COMPLETED",
            "replacement_items": [
                {
                    "request_item_id": request_item_ids[str(seeded["order_item_id"])],
                    "imeis": [seeded["replacement_imei"]],
                }
            ],
        },
    )
    assert incomplete.status_code == 400, incomplete.text

    completed = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={
            "status": "COMPLETED",
            "note": "Đã cấp đủ hai thiết bị thay thế.",
            "replacement_items": [
                {
                    "request_item_id": request_item_ids[str(seeded["order_item_id"])],
                    "imeis": [seeded["replacement_imei"]],
                },
                {
                    "request_item_id": request_item_ids[str(serial_order_item_id)],
                    "serial_numbers": [replacement_serial],
                },
            ],
        },
    )
    assert completed.status_code == 200, completed.text

    stored_items = (
        await db_session.execute(
            text(
                """
                SELECT order_item_id, replacement_imeis, replacement_serial_numbers
                FROM return_request_items
                WHERE request_id = :request_id
                """
            ),
            {"request_id": request_id},
        )
    ).mappings().all()
    stored_by_order_item = {
        str(row["order_item_id"]): row
        for row in stored_items
    }
    paired_item = stored_by_order_item[str(seeded["order_item_id"])]
    serial_item = stored_by_order_item[str(serial_order_item_id)]
    assert paired_item["replacement_imeis"] == [seeded["replacement_imei"]]
    assert paired_item["replacement_serial_numbers"] == [seeded["replacement_serial"]]
    assert serial_item["replacement_imeis"] == []
    assert serial_item["replacement_serial_numbers"] == [replacement_serial]

    serial_statuses = dict(
        (
            await db_session.execute(
                text(
                    """
                    SELECT serial_number, status
                    FROM product_serial_numbers
                    WHERE serial_number IN (
                        :paired_new, :paired_old, :serial_new, :serial_old
                    )
                    """
                ),
                {
                    "paired_new": seeded["replacement_serial"],
                    "paired_old": seeded["old_serial"],
                    "serial_new": replacement_serial,
                    "serial_old": old_serial,
                },
            )
        ).all()
    )
    assert serial_statuses[seeded["replacement_serial"]] == "SOLD"
    assert serial_statuses[seeded["old_serial"]] == "DEFECTIVE_RETURNED"
    assert serial_statuses[replacement_serial] == "SOLD"
    assert serial_statuses[old_serial] == "DEFECTIVE_RETURNED"

    outbound_summary = (
        await db_session.execute(
            text(
                """
                SELECT COUNT(l.id)::int AS line_count,
                       SUM(l.approved_quantity)::int AS total_quantity
                FROM inventory_documents d
                JOIN inventory_document_lines l ON l.document_id = d.id
                WHERE d.return_request_id = :request_id
                """
            ),
            {"request_id": request_id},
        )
    ).mappings().one()
    consumed_allocations = await db_session.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM after_sales_allocations
            WHERE reference_type = 'RETURN'
              AND reference_id = :request_id
              AND status = 'CONSUMED'
            """
        ),
        {"request_id": request_id},
    )
    assert outbound_summary["line_count"] == 2
    assert outbound_summary["total_quantity"] == 2
    assert consumed_allocations == 2

    admin_list = await api_client.get(
        "/api/admin/after-sales/returns",
        headers=admin_headers,
    )
    assert admin_list.status_code == 200, admin_list.text
    listed = next(item for item in admin_list.json()["items"] if item["id"] == request_id)
    listed_serial_item = next(
        item for item in listed["items"]
        if item["orderItemId"] == str(serial_order_item_id)
    )
    assert listed_serial_item["replacementSerialNumbers"] == [replacement_serial]


@pytest.mark.workflow
async def test_create_return_fails_when_policy_checkboxes_false(
    api_client,
    db_session,
    customer_user,
    customer_headers,
):
    product_id = uuid4()
    order_id = uuid4()
    order_item_id = uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, stock_quantity,
                status, warranty_period
            )
            VALUES (
                :product_id, :sku, 'Điện thoại kiểm thử checklist', 'dien-thoai-checklist',
                'PHONE', 'Hãng kiểm thử', 5000000, 0, 'ACTIVE', 12
            )
            """
        ),
        {
            "product_id": product_id,
            "sku": f"TEST-CK-{uuid4().hex[:8].upper()}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO orders (
                id, user_id, order_code, status, payment_method, payment_status,
                subtotal_amount, discount_amount, shipping_fee, total_amount,
                recipient_name, recipient_phone, shipping_address, completed_at
            )
            VALUES (
                :order_id, :user_id, :order_code, 'COMPLETED', 'COD', 'PAID',
                5000000, 0, 0, 5000000,
                'Khách hàng kiểm thử', '0900000003',
                '456 Đường kiểm thử, Thành phố Hồ Chí Minh', NOW()
            )
            """
        ),
        {
            "order_id": order_id,
            "user_id": customer_user["id"],
            "order_code": f"TEST-CK-{uuid4().hex[:8].upper()}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO order_items (
                id, order_id, product_id, product_name, quantity, unit_price, total_price
            )
            VALUES (
                :order_item_id, :order_id, :product_id,
                'Điện thoại kiểm thử checklist', 1, 5000000, 5000000
            )
            """
        ),
        {
            "product_id": product_id,
            "order_id": order_id,
            "order_item_id": order_item_id,
        },
    )
    await db_session.commit()

    # Create request with one checkbox as False
    response = await api_client.post(
        "/api/me/returns",
        headers=customer_headers,
        json={
            "order_id": str(order_id),
            "reason": "Mua nhầm sản phẩm cần trả lại hàng hoàn tiền.",
            "items": [{"order_item_id": str(order_item_id), "quantity": 1}],
            "has_accessories": False,
            "good_appearance": True,
            "account_unlocked": True,
            "has_vat_invoice": True,
        },
    )
    assert response.status_code == 400
    assert "Yêu cầu đổi trả chỉ được chấp nhận" in response.text


@pytest.mark.workflow
async def test_multiple_same_order_item_in_single_return(
    api_client,
    db_session,
    customer_user,
    customer_headers,
    admin_headers,
):
    product_id = uuid4()
    order_id = uuid4()
    order_item_id = uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, stock_quantity,
                status, warranty_period
            )
            VALUES (
                :product_id, :sku, 'Điện thoại mua số lượng 2', 'dien-thoai-sl-2',
                'PHONE', 'Hãng kiểm thử', 5000000, 0, 'ACTIVE', 12
            )
            """
        ),
        {
            "product_id": product_id,
            "sku": f"TEST-SL2-{uuid4().hex[:8].upper()}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO orders (
                id, user_id, order_code, status, payment_method, payment_status,
                subtotal_amount, discount_amount, shipping_fee, total_amount,
                recipient_name, recipient_phone, shipping_address, completed_at
            )
            VALUES (
                :order_id, :user_id, :order_code, 'COMPLETED', 'COD', 'PAID',
                10000000, 0, 0, 10000000,
                'Khách hàng kiểm thử', '0900000003',
                '456 Đường kiểm thử, Thành phố Hồ Chí Minh', NOW()
            )
            """
        ),
        {
            "order_id": order_id,
            "user_id": customer_user["id"],
            "order_code": f"TEST-SL2-{uuid4().hex[:8].upper()}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO order_items (
                id, order_id, product_id, product_name, quantity, unit_price, total_price
            )
            VALUES (
                :order_item_id, :order_id, :product_id,
                'Điện thoại mua số lượng 2', 2, 5000000, 10000000
            )
            """
        ),
        {
            "product_id": product_id,
            "order_id": order_id,
            "order_item_id": order_item_id,
        },
    )
    await db_session.commit()

    imei1 = _new_test_imei("35")
    imei2 = _new_test_imei("86")
    await db_session.execute(
        text(
            """
            INSERT INTO product_imeis (id, product_id, imei, status, sold_order_id, sold_at)
            VALUES
                (:id1, :product_id, :imei1, 'SOLD', :order_id, NOW()),
                (:id2, :product_id, :imei2, 'SOLD', :order_id, NOW())
            """
        ),
        {
            "id1": uuid4(),
            "id2": uuid4(),
            "product_id": product_id,
            "imei1": imei1,
            "imei2": imei2,
            "order_id": order_id,
        },
    )
    await db_session.commit()

    # Return request containing multiple items for the same order_item_id but different IMEIs
    response = await api_client.post(
        "/api/me/returns",
        headers=customer_headers,
        json={
            "order_id": str(order_id),
            "reason": "Lỗi phần cứng cả hai thiết bị.",
            "items": [
                {"order_item_id": str(order_item_id), "quantity": 1, "imei": imei1},
                {"order_item_id": str(order_item_id), "quantity": 1, "imei": imei2},
            ],
            "has_accessories": True,
            "good_appearance": True,
            "account_unlocked": True,
            "has_vat_invoice": True,
        },
    )
    assert response.status_code == 201, response.text
    request_id = response.json()["id"]

    rx = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={"status": "RECEIVED", "note": "Received"},
    )
    assert rx.status_code == 200, rx.text

    qc_start = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={"status": "QC_IN_PROGRESS", "note": "QC started"},
    )
    assert qc_start.status_code == 200, qc_start.text

    inspect_res = await api_client.post(
        f"/api/admin/after-sales/returns/{request_id}/inspection",
        headers=admin_headers,
        json={
            "result": "APPROVE_REFUND",
            "qc_note": "Cả hai máy đều lỗi và đủ điều kiện hoàn tiền.",
            "customer_fault": False,
        },
    )
    assert inspect_res.status_code == 200, inspect_res.text

    refund_processing = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={"status": "REFUND_PROCESSING", "note": "Processing refund"},
    )
    assert refund_processing.status_code == 200, refund_processing.text

    refund_res = await api_client.patch(
        f"/api/admin/after-sales/returns/{request_id}/status",
        headers=admin_headers,
        json={
            "status": "COMPLETED",
            "note": "Refund completed",
            "refund_transaction_ref": "REF-SL2-12345",
            "refund_proof_url": "http://example.com/proof.jpg",
        },
    )
    assert refund_res.status_code == 200, refund_res.text
