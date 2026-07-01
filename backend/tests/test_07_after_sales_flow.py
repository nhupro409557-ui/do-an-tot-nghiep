from uuid import uuid4

import pytest
from sqlalchemy import text


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

    admin_list = await api_client.get(
        "/api/admin/after-sales/returns",
        headers=admin_headers,
    )
    assert admin_list.status_code == 200, admin_list.text
    assert request_id in admin_list.text

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

    for status in ["RECEIVED", "QC_IN_PROGRESS", "WARRANTY_ACCEPTED"]:
        updated = await api_client.patch(
            f"/api/admin/after-sales/warranties/{request_id}/status",
            headers=admin_headers,
            json={"status": status, "note": f"Chuyển sang {status}"},
        )
        assert updated.status_code == 200, updated.text

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
