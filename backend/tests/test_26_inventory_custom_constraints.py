import json
from uuid import uuid4
import pytest
from sqlalchemy import text


@pytest.mark.workflow
async def test_constraints_adjustment_blocked_for_imei_product(api_client, db_session, admin_headers):
    # Tạo sản phẩm có trackImei=True
    product_id = uuid4()
    sku = f"IMEI-ADJ-{uuid4().hex[:6].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'PHONE', 'Apple',
                20000000, 20000000, 0, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "iPhone có IMEI",
            "slug": f"iphone-co-imei-{uuid4().hex[:6]}",
            "sales_config": json.dumps(
                {
                    "imeiPolicy": {"mode": "MANUAL", "trackImei": True},
                    "serialPolicy": {"mode": "MANUAL", "trackSerialNumber": False},
                }
            ),
        },
    )
    await db_session.commit()

    # Tạo phiếu điều chỉnh tồn
    response = await api_client.post(
        "/api/admin/inventory/adjustments",
        headers=admin_headers,
        json={
            "referenceCode": f"ADJ-BLK-{uuid4().hex[:8].upper()}",
            "reason": "DIEU_CHINH_THU_CONG",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": None,
                    "currentQuantity": 0,
                    "newQuantity": 1,
                    "reason": "Điều chỉnh test chặn IMEI",
                }
            ],
        },
    )
    # Kỳ vọng bị chặn ngay với status_code = 400
    assert response.status_code == 400
    assert "quản lý IMEI/serial" in response.text


@pytest.mark.workflow
async def test_constraints_stock_count_lot_adjustments(api_client, db_session, admin_headers, approver_headers):
    # Tạo sản phẩm bình thường không quản lý IMEI/Serial
    product_id = uuid4()
    sku = f"CNT-LOT-{uuid4().hex[:6].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'ACCESSORY', 'Sony',
                1000000, 1000000, 5, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Tai nghe Sony",
            "slug": f"tai-nghe-sony-{uuid4().hex[:6]}",
            "sales_config": json.dumps(
                {
                    "imeiPolicy": {"mode": "MANUAL", "trackImei": False},
                    "serialPolicy": {"mode": "MANUAL", "trackSerialNumber": False},
                }
            ),
        },
    )
    location_id = await db_session.scalar(text("SELECT id FROM inventory_locations WHERE code = 'A-01-01'"))

    # Tạo level và lot ban đầu
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_levels (id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost)
            VALUES (gen_random_uuid(), :product_id, NULL, :location_id, 5, 0, 800000)
            """
        ),
        {"product_id": product_id, "location_id": location_id},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_lots (id, lot_code, product_id, variant_id, location_id, initial_quantity, remaining_quantity, unit_cost, received_at, status)
            VALUES (gen_random_uuid(), :lot_code, :product_id, NULL, :location_id, 5, 5, 800000, NOW() - INTERVAL '1 day', 'ACTIVE')
            """
        ),
        {"lot_code": f"LOT-INIT-{uuid4().hex[:6]}".upper(), "product_id": product_id, "location_id": location_id},
    )
    await db_session.commit()

    # Thử kiểm kê lệch thừa: thực đếm 7 (variance = +2)
    ref_code = f"CNT-{uuid4().hex[:8].upper()}"
    res_create = await api_client.post(
        "/api/admin/inventory/stock-counts",
        headers=admin_headers,
        json={
            "referenceCode": ref_code,
            "locationCode": "A-01-01",
            "reason": "KIEM_KE_THUONG_KY",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": None,
                    "expectedQuantity": 5,
                    "countedQuantity": 7,
                }
            ],
        },
    )
    assert res_create.status_code == 200, res_create.text

    # Duyệt kiểm kê
    res_approve = await api_client.patch(
        f"/api/admin/inventory/stock-counts/{ref_code}/status",
        headers=approver_headers,
        json={"status": "APPROVED"},
    )
    assert res_approve.status_code == 200, res_approve.text

    # Kiểm tra xem có tạo thêm lô mới không
    lots = (
        await db_session.execute(
            text("SELECT lot_code, remaining_quantity, unit_cost FROM inventory_lots WHERE product_id = :product_id"),
            {"product_id": product_id},
        )
    ).mappings().all()
    assert len(lots) == 2
    # Một lô cũ 5 cái, một lô mới chênh lệch thừa 2 cái
    assert sum(r["remaining_quantity"] for r in lots) == 7


@pytest.mark.workflow
async def test_constraints_transfer_mismatched_pairs_blocked(api_client, db_session, admin_headers):
    # Tạo sản phẩm quản lý cả hai (trackImei=True, trackSerialNumber=True)
    product_id = uuid4()
    sku = f"TRF-PAIR-{uuid4().hex[:6].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'PHONE', 'Samsung',
                15000000, 15000000, 1, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Samsung có IMEI và Serial",
            "slug": f"samsung-imei-serial-{uuid4().hex[:6]}",
            "sales_config": json.dumps(
                {
                    "imeiPolicy": {"mode": "MANUAL", "trackImei": True},
                    "serialPolicy": {"mode": "MANUAL", "trackSerialNumber": True},
                }
            ),
        },
    )
    loc_from = await db_session.scalar(text("SELECT id FROM inventory_locations WHERE code = 'A-01-01'"))
    loc_to = await db_session.scalar(text("SELECT id FROM inventory_locations WHERE code = 'A-01-02'"))

    # Đưa vào 1 level và 1 cặp identifier pair
    imei_correct = "888888888888888"
    serial_correct = "SAMSUNG-SN-111"

    await db_session.execute(
        text(
            """
            INSERT INTO inventory_levels (id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost)
            VALUES (gen_random_uuid(), :product_id, NULL, :location_id, 1, 0, 12000000)
            """
        ),
        {"product_id": product_id, "location_id": loc_from},
    )
    # Chèn product_imeis và product_serial_numbers TRƯỚC để thỏa mãn khóa ngoại
    await db_session.execute(
        text(
            """
            INSERT INTO product_imeis (id, product_id, variant_id, location_id, imei, status)
            VALUES (gen_random_uuid(), :product_id, NULL, :location_id, :imei, 'IN_STOCK')
            """
        ),
        {"product_id": product_id, "location_id": loc_from, "imei": imei_correct},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (id, product_id, variant_id, location_id, serial_number, status)
            VALUES (gen_random_uuid(), :product_id, NULL, :location_id, :serial, 'IN_STOCK')
            """
        ),
        {"product_id": product_id, "location_id": loc_from, "serial": serial_correct},
    )
    # Chèn cặp ghép sau khi đã có IMEI và Serial
    await db_session.execute(
        text(
            """
            INSERT INTO product_identifier_pairs (id, product_id, variant_id, imei1, serial_number)
            VALUES (gen_random_uuid(), :product_id, NULL, :imei1, :serial)
            """
        ),
        {"product_id": product_id, "imei1": imei_correct, "serial": serial_correct},
    )
    await db_session.commit()

    # Thử chuyển với IMEI đúng nhưng Serial sai (lệch cặp)
    res_bad = await api_client.post(
        "/api/admin/inventory/transfers",
        headers=admin_headers,
        json={
            "referenceCode": f"TRF-BAD-{uuid4().hex[:8].upper()}",
            "reason": "LUAN_CHUYEN",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": None,
                    "fromLocationId": str(loc_from),
                    "toLocationId": str(loc_to),
                    "quantity": 1,
                    "imeis": [imei_correct],
                    "serialNumbers": ["SAMSUNG-SN-WRONG"],
                }
            ],
        },
    )
    # Kỳ vọng bị chặn với status_code = 400
    assert res_bad.status_code == 400
    assert "ghép cặp" in res_bad.text or "yêu cầu" in res_bad.text


@pytest.mark.workflow
async def test_constraints_internal_hold_lock_and_unlock_identifiers(api_client, db_session, admin_headers, approver_headers):
    # Tạo sản phẩm quản lý IMEI
    product_id = uuid4()
    sku = f"HLD-IMEI-{uuid4().hex[:6].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'PHONE', 'OPPO',
                8000000, 8000000, 1, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "OPPO có IMEI",
            "slug": f"oppo-imei-{uuid4().hex[:6]}",
            "sales_config": json.dumps(
                {
                    "imeiPolicy": {"mode": "MANUAL", "trackImei": True},
                    "serialPolicy": {"mode": "MANUAL", "trackSerialNumber": False},
                }
            ),
        },
    )
    location_id = await db_session.scalar(text("SELECT id FROM inventory_locations WHERE code = 'A-01-01'"))

    imei_val = "999999999999999"
    serial_val = "OPPO-SN-999"
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_levels (id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost)
            VALUES (gen_random_uuid(), :product_id, NULL, :location_id, 1, 0, 6000000)
            """
        ),
        {"product_id": product_id, "location_id": location_id},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_imeis (id, product_id, variant_id, location_id, imei, status)
            VALUES (gen_random_uuid(), :product_id, NULL, :location_id, :imei, 'IN_STOCK')
            """
        ),
        {"product_id": product_id, "location_id": location_id, "imei": imei_val},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (id, product_id, variant_id, location_id, serial_number, status)
            VALUES (gen_random_uuid(), :product_id, NULL, :location_id, :serial, 'IN_STOCK')
            """
        ),
        {"product_id": product_id, "location_id": location_id, "serial": serial_val},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_identifier_pairs (id, product_id, variant_id, imei1, serial_number)
            VALUES (gen_random_uuid(), :product_id, NULL, :imei1, :serial)
            """
        ),
        {"product_id": product_id, "imei1": imei_val, "serial": serial_val},
    )
    await db_session.commit()

    # Thử tạo phiếu giữ nội bộ nhưng không gửi kèm IMEI/Serial (do trackImei=True)
    res_hold_no_imei = await api_client.post(
        "/api/admin/inventory/internal-holds",
        headers=admin_headers,
        json={
            "referenceCode": f"HLD-NO-{uuid4().hex[:8].upper()}",
            "holdType": "INTERNAL_HOLD",
            "reason": "Test thieu IMEI",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": None,
                    "locationId": str(location_id),
                    "quantity": 1,
                }
            ],
        },
    )
    assert res_hold_no_imei.status_code == 400
    assert "quản lý IMEI" in res_hold_no_imei.text or "quản lý serial" in res_hold_no_imei.text or "yêu cầu" in res_hold_no_imei.text

    # Tạo phiếu giữ kèm IMEI & Serial hợp lệ (vì hệ thống tự coi imei policy = serial policy)
    hold_ref = f"HLD-OK-{uuid4().hex[:8].upper()}"
    res_hold_ok = await api_client.post(
        "/api/admin/inventory/internal-holds",
        headers=admin_headers,
        json={
            "referenceCode": hold_ref,
            "holdType": "INTERNAL_HOLD",
            "reason": "Giữ hàng trưng bày OPPO",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": None,
                    "locationId": str(location_id),
                    "quantity": 1,
                    "imeis": [imei_val],
                    "serialNumbers": [serial_val],
                }
            ],
        },
    )
    assert res_hold_ok.status_code == 200, res_hold_ok.text

    # Duyệt phiếu hold -> chuyển trạng thái IMEI & Serial sang RESERVED
    res_app = await api_client.patch(
        f"/api/admin/inventory/internal-holds/{hold_ref}/status",
        headers=approver_headers,
        json={"status": "APPROVED"},
    )
    assert res_app.status_code == 200, res_app.text

    # Check status imei & serial trong db
    imei_status = await db_session.scalar(
        text("SELECT status FROM product_imeis WHERE imei = :imei"),
        {"imei": imei_val},
    )
    assert imei_status == "RESERVED"

    serial_status = await db_session.scalar(
        text("SELECT status FROM product_serial_numbers WHERE serial_number = :serial"),
        {"serial": serial_val},
    )
    assert serial_status == "RESERVED"

    # Giải phóng phiếu hold (COMPLETED) -> chuyển trạng thái IMEI & Serial về lại IN_STOCK
    res_comp = await api_client.patch(
        f"/api/admin/inventory/internal-holds/{hold_ref}/status",
        headers=approver_headers,
        json={"status": "COMPLETED"},
    )
    assert res_comp.status_code == 200, res_comp.text

    imei_status_after = await db_session.scalar(
        text("SELECT status FROM product_imeis WHERE imei = :imei"),
        {"imei": imei_val},
    )
    assert imei_status_after == "IN_STOCK"

    serial_status_after = await db_session.scalar(
        text("SELECT status FROM product_serial_numbers WHERE serial_number = :serial"),
        {"serial": serial_val},
    )
    assert serial_status_after == "IN_STOCK"


@pytest.mark.workflow
async def test_constraints_location_modifications_with_stock(api_client, db_session, admin_headers):
    # Lấy thông tin kệ A-01-01 (đã có stock từ test trước hoặc tạo mới)
    row = await db_session.execute(
        text("SELECT id, code, purpose FROM inventory_locations WHERE code = 'A-01-01'")
    )
    loc = row.mappings().first()
    assert loc is not None
    location_id = loc["id"]

    # Đảm bảo kệ A-01-01 có tồn kho
    # (Nếu chưa có, insert 1 record vào inventory_levels)
    existing_level = await db_session.scalar(
        text("SELECT COUNT(*) FROM inventory_levels WHERE location_id = :location_id AND on_hand_quantity > 0"),
        {"location_id": location_id}
    )
    if not existing_level:
        # Lấy 1 product_id
        product_id = await db_session.scalar(text("SELECT id FROM products LIMIT 1"))
        await db_session.execute(
            text(
                """
                INSERT INTO inventory_levels (id, product_id, variant_id, location_id, on_hand_quantity, reserved_quantity, average_unit_cost)
                VALUES (gen_random_uuid(), :product_id, NULL, :location_id, 1, 0, 100000)
                """
            ),
            {"product_id": product_id, "location_id": location_id}
        )
        await db_session.commit()

    # 1. Thử thay đổi mục đích (purpose) từ STORAGE sang QC -> Phải bị chặn (400)
    res_purpose = await api_client.put(
        f"/api/admin/inventory/locations/{location_id}",
        headers=admin_headers,
        json={
            "code": "A-01-01",
            "name": "Kệ A-01-01",
            "zone": "Khu A",
            "purpose": "QC",
            "sortOrder": 1,
            "allowMixedSku": True,
            "lengthCm": 100,
            "widthCm": 100,
            "heightCm": 100,
            "usableRatio": 0.75
        }
    )
    assert res_purpose.status_code == 400
    assert "mục đích kệ" in res_purpose.text

    # 2. Thử giảm kích thước / dung lượng (capacity) quá mức -> Phải bị chặn (400)
    # Vì on-hand > 0, usedVolumeCm3 chắc chắn > 0 (do _effective_package_volume_cm3 sinh ra thể tích dương)
    res_capacity = await api_client.put(
        f"/api/admin/inventory/locations/{location_id}",
        headers=admin_headers,
        json={
            "code": "A-01-01",
            "name": "Kệ A-01-01",
            "zone": "Khu A",
            "purpose": "STORAGE",
            "sortOrder": 1,
            "allowMixedSku": True,
            "lengthCm": 0.1,  # Dung tích cực nhỏ
            "widthCm": 0.1,
            "heightCm": 0.1,
            "usableRatio": 0.1
        }
    )
    assert res_capacity.status_code == 400
    assert "Dung lượng mới" in res_capacity.text

    # 3. Thử khóa kệ (isActive = False) -> Phải bị chặn (400)
    res_status = await api_client.patch(
        f"/api/admin/inventory/locations/{location_id}/status",
        headers=admin_headers,
        json={"isActive": False}
    )
    assert res_status.status_code == 400
    assert "Kệ còn tồn kho" in res_status.text
