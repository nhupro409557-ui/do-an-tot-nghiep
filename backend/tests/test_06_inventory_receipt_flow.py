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


@pytest.mark.workflow
async def test_quarantine_receipt_posts_to_qc_location_without_sellable_stock(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    product_id = uuid4()
    variant_id = uuid4()
    qc_location_id = uuid4()
    qc_location_code = f"QC-{uuid4().hex[:6].upper()}"
    sku = f"TEST-QC-{uuid4().hex[:8].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_locations (
                id, code, name, location_type, purpose, status, is_default
            )
            VALUES (
                :id, :code, 'Kệ QC kiểm thử', 'WAREHOUSE', 'QC', 'ACTIVE', FALSE
            )
            ON CONFLICT (code) DO UPDATE
            SET purpose = 'QC',
                status = 'ACTIVE',
                updated_at = NOW()
            RETURNING id
            """
        ),
        {"id": qc_location_id, "code": qc_location_code},
    )
    qc_location_id = await db_session.scalar(
        text("SELECT id FROM inventory_locations WHERE code = :code"),
        {"code": qc_location_code},
    )
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
            "name": "Sản phẩm nhập cách ly kiểm thử",
            "slug": f"san-pham-nhap-cach-ly-{uuid4().hex[:8]}",
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

    reference_code = f"TEST-QC-IN-{uuid4().hex[:8].upper()}"
    created = await api_client.post(
        "/api/admin/inventory/receipts",
        headers={**admin_headers, "Idempotency-Key": reference_code},
        json={
            "referenceCode": reference_code,
            "receiptReasonCode": "NK_MUA",
            "supplierName": "Nhà cung cấp kiểm thử",
            "qualityStatus": "PENDING",
            "quarantine": True,
            "quarantineLocation": "Kệ QC kiểm thử",
            "status": "DRAFT",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id),
                    "quantity": 2,
                    "unitCost": 400000,
                    "warehouseLocationId": str(qc_location_id),
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

    sellable_stock = await db_session.scalar(
        text("SELECT stock_quantity FROM product_variants WHERE id = :variant_id"),
        {"variant_id": variant_id},
    )
    level_quantity = await db_session.scalar(
        text(
            """
            SELECT on_hand_quantity
            FROM inventory_levels
            WHERE variant_id = :variant_id
              AND location_id = :location_id
            """
        ),
        {"variant_id": variant_id, "location_id": qc_location_id},
    )
    lot_quantity = await db_session.scalar(
        text(
            """
            SELECT COALESCE(SUM(remaining_quantity), 0)::int
            FROM inventory_lots
            WHERE variant_id = :variant_id
              AND location_id = :location_id
              AND source_reference = :reference_code
            """
        ),
        {
            "variant_id": variant_id,
            "location_id": qc_location_id,
            "reference_code": reference_code,
        },
    )
    assert sellable_stock == 0
    assert level_quantity == 2
    assert lot_quantity == 2


@pytest.mark.workflow
async def test_quarantine_receipt_activates_reverses_and_cancels_identifier_pairs(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    product_id = uuid4()
    variant_id = uuid4()
    qc_location_id = uuid4()
    qc_location_code = f"QC-{uuid4().hex[:6].upper()}"
    sku = f"TEST-QC-ID-{uuid4().hex[:6].upper()}"
    imei = f"86{uuid4().int % 10**13:013d}"
    secondary_imei = f"35{uuid4().int % 10**13:013d}"
    serial_number = f"SN-{uuid4().hex[:10].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_locations (
                id, code, name, location_type, purpose, status, is_default
            )
            VALUES (
                :id, :code, 'Kệ QC mã định danh', 'WAREHOUSE', 'QC', 'ACTIVE', FALSE
            )
            """
        ),
        {"id": qc_location_id, "code": qc_location_code},
    )
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, stock_quantity,
                status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'PHONE', 'Hãng kiểm thử',
                500000, 0, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Sản phẩm cách ly có mã định danh",
            "slug": f"san-pham-qc-imei-{uuid4().hex[:8]}",
            "sales_config": json.dumps(
                {
                    "imeiPolicy": {"mode": "MANUAL", "trackImei": True},
                    "serialPolicy": {
                        "mode": "MANUAL",
                        "trackSerialNumber": True,
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

    reference_code = f"TEST-QC-ID-{uuid4().hex[:8].upper()}"
    created = await api_client.post(
        "/api/admin/inventory/receipts",
        headers={**admin_headers, "Idempotency-Key": reference_code},
        json={
            "referenceCode": reference_code,
            "receiptReasonCode": "NK_MUA",
            "supplierName": "Nhà cung cấp kiểm thử",
            "qualityStatus": "PENDING",
            "quarantine": True,
            "quarantineLocation": "Kệ QC mã định danh",
            "status": "DRAFT",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id),
                    "quantity": 1,
                    "unitCost": 400000,
                    "warehouseLocationId": str(qc_location_id),
                }
            ],
        },
    )
    assert created.status_code == 200, created.text

    processing = await api_client.patch(
        f"/api/admin/inventory/receipts/{reference_code}/status",
        headers=admin_headers,
        json={"status": "PROCESSING_IMEI"},
    )
    assert processing.status_code == 200, processing.text
    line_id = await db_session.scalar(
        text(
            """
            SELECT l.id
            FROM inventory_document_lines l
            JOIN inventory_documents d ON d.id = l.document_id
            WHERE d.document_no = :reference_code
            """
        ),
        {"reference_code": reference_code},
    )
    submitted = await api_client.post(
        f"/api/admin/inventory/receipts/{reference_code}/imeis",
        headers=admin_headers,
        json={
            "lines": [
                {
                    "lineId": str(line_id),
                    "imeis": [imei],
                    "secondaryImeis": [secondary_imei],
                    "serialNumbers": [serial_number],
                }
            ]
        },
    )
    assert submitted.status_code == 200, submitted.text
    listed = await api_client.get(
        "/api/admin/inventory/receipts",
        headers=admin_headers,
    )
    assert listed.status_code == 200, listed.text
    listed_receipt = next(
        item
        for item in listed.json()["items"]
        if item["referenceCode"] == reference_code
    )
    assert listed_receipt["lines"][0]["secondaryImeis"] == [secondary_imei]

    for target_status in ("APPROVED", "COMPLETED"):
        changed = await api_client.patch(
            f"/api/admin/inventory/receipts/{reference_code}/status",
            headers=approver_headers,
            json={"status": target_status},
        )
        assert changed.status_code == 200, (
            f"{target_status}: {changed.status_code} {changed.text}"
        )

    imei_rows = (
        await db_session.execute(
            text(
                """
                SELECT imei, status, location_id
                FROM product_imeis
                WHERE imei IN (:imei, :secondary_imei)
                """
            ),
            {"imei": imei, "secondary_imei": secondary_imei},
        )
    ).mappings().all()
    serial_row = (
        await db_session.execute(
            text(
                """
                SELECT status, location_id
                FROM product_serial_numbers
                WHERE serial_number = :serial_number
            """
            ),
            {"serial_number": serial_number},
        )
    ).mappings().one()
    sellable_stock = await db_session.scalar(
        text("SELECT stock_quantity FROM product_variants WHERE id = :variant_id"),
        {"variant_id": variant_id},
    )
    assert {row["imei"] for row in imei_rows} == {imei, secondary_imei}
    assert all(row["status"] == "INSPECTION_PENDING" for row in imei_rows)
    assert serial_row["status"] == "INSPECTION_PENDING"
    assert all(row["location_id"] == qc_location_id for row in imei_rows)
    assert serial_row["location_id"] == qc_location_id
    assert sellable_stock == 0

    reversed_receipt = await api_client.post(
        f"/api/admin/inventory/receipts/{reference_code}/reverse",
        headers=approver_headers,
        json={
            "reason": "Đảo phiếu cách ly kiểm thử",
            "note": "Xác nhận thu hồi đồng bộ IMEI1, IMEI2 và serial number.",
        },
    )
    assert reversed_receipt.status_code == 200, reversed_receipt.text
    reversal_reference_code = reversed_receipt.json()["reversalReferenceCode"]

    reversed_imei_rows = (
        await db_session.execute(
            text(
                """
                SELECT imei, status, location_id
                FROM product_imeis
                WHERE imei IN (:imei, :secondary_imei)
                """
            ),
            {"imei": imei, "secondary_imei": secondary_imei},
        )
    ).mappings().all()
    reversed_serial_row = (
        await db_session.execute(
            text(
                """
                SELECT status, location_id
                FROM product_serial_numbers
                WHERE product_id = :product_id
                  AND serial_number = :serial_number
                """
            ),
            {"product_id": product_id, "serial_number": serial_number},
        )
    ).mappings().one()
    identifier_pair = (
        await db_session.execute(
            text(
                """
                SELECT imei1, imei2, serial_number
                FROM product_identifier_pairs
                WHERE product_id = :product_id
                  AND serial_number = :serial_number
                """
            ),
            {"product_id": product_id, "serial_number": serial_number},
        )
    ).mappings().one()
    original_receipt_status = await db_session.scalar(
        text("SELECT status FROM inventory_documents WHERE document_no = :reference_code"),
        {"reference_code": reference_code},
    )
    reversal_secondary_imeis = await db_session.scalar(
        text(
            """
            SELECT l.metadata->'secondaryImeis'
            FROM inventory_documents d
            JOIN inventory_document_lines l ON l.document_id = d.id
            WHERE d.document_no = :reversal_reference_code
            """
        ),
        {"reversal_reference_code": reversal_reference_code},
    )
    remaining_level_quantity = await db_session.scalar(
        text(
            """
            SELECT COALESCE((
                SELECT on_hand_quantity
                FROM inventory_levels
                WHERE product_id = :product_id
                  AND variant_id = :variant_id
                  AND location_id = :location_id
            ), 0)
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "location_id": qc_location_id,
        },
    )
    sellable_stock_after_reversal = await db_session.scalar(
        text("SELECT stock_quantity FROM product_variants WHERE id = :variant_id"),
        {"variant_id": variant_id},
    )
    assert {row["imei"] for row in reversed_imei_rows} == {imei, secondary_imei}
    assert all(row["status"] == "REVERSED" for row in reversed_imei_rows)
    assert all(row["location_id"] is None for row in reversed_imei_rows)
    assert reversed_serial_row["status"] == "REVERSED"
    assert reversed_serial_row["location_id"] is None
    assert dict(identifier_pair) == {
        "imei1": imei,
        "imei2": secondary_imei,
        "serial_number": serial_number,
    }
    assert original_receipt_status == "REVERSED"
    assert reversal_secondary_imeis == [secondary_imei]
    assert remaining_level_quantity == 0
    assert sellable_stock_after_reversal == 0

    cancelled_imei = f"86{uuid4().int % 10**13:013d}"
    cancelled_secondary_imei = f"35{uuid4().int % 10**13:013d}"
    cancelled_serial_number = f"SN-{uuid4().hex[:10].upper()}"
    cancelled_reference_code = f"TEST-QC-CANCEL-{uuid4().hex[:8].upper()}"
    created_for_cancellation = await api_client.post(
        "/api/admin/inventory/receipts",
        headers={**admin_headers, "Idempotency-Key": cancelled_reference_code},
        json={
            "referenceCode": cancelled_reference_code,
            "receiptReasonCode": "NK_MUA",
            "supplierName": "Nhà cung cấp kiểm thử",
            "qualityStatus": "PENDING",
            "quarantine": True,
            "quarantineLocation": "Kệ QC mã định danh",
            "status": "DRAFT",
            "lines": [
                {
                    "productId": str(product_id),
                    "variantId": str(variant_id),
                    "quantity": 1,
                    "unitCost": 400000,
                    "warehouseLocationId": str(qc_location_id),
                }
            ],
        },
    )
    assert created_for_cancellation.status_code == 200, created_for_cancellation.text
    processing_for_cancellation = await api_client.patch(
        f"/api/admin/inventory/receipts/{cancelled_reference_code}/status",
        headers=admin_headers,
        json={"status": "PROCESSING_IMEI"},
    )
    assert processing_for_cancellation.status_code == 200, processing_for_cancellation.text
    cancelled_line_id = await db_session.scalar(
        text(
            """
            SELECT l.id
            FROM inventory_document_lines l
            JOIN inventory_documents d ON d.id = l.document_id
            WHERE d.document_no = :reference_code
            """
        ),
        {"reference_code": cancelled_reference_code},
    )
    submitted_for_cancellation = await api_client.post(
        f"/api/admin/inventory/receipts/{cancelled_reference_code}/imeis",
        headers=admin_headers,
        json={
            "lines": [
                {
                    "lineId": str(cancelled_line_id),
                    "imeis": [cancelled_imei],
                    "secondaryImeis": [cancelled_secondary_imei],
                    "serialNumbers": [cancelled_serial_number],
                }
            ]
        },
    )
    assert submitted_for_cancellation.status_code == 200, submitted_for_cancellation.text
    pending_pair_count = await db_session.scalar(
        text(
            """
            SELECT COUNT(*)
            FROM product_identifier_pairs
            WHERE source_reference = :reference_code
            """
        ),
        {"reference_code": cancelled_reference_code},
    )
    assert pending_pair_count == 1

    cancelled_receipt = await api_client.patch(
        f"/api/admin/inventory/receipts/{cancelled_reference_code}/status",
        headers=approver_headers,
        json={
            "status": "CANCELLED",
            "cancelReason": "Hủy phiếu trước khi hoàn tất để kiểm tra dọn mã chờ.",
        },
    )
    assert cancelled_receipt.status_code == 200, cancelled_receipt.text
    remaining_pending_identifiers = await db_session.scalar(
        text(
            """
            SELECT (
                SELECT COUNT(*)
                FROM product_imeis
                WHERE source_reference = :reference_code
            ) + (
                SELECT COUNT(*)
                FROM product_serial_numbers
                WHERE source_reference = :reference_code
            ) + (
                SELECT COUNT(*)
                FROM product_identifier_pairs
                WHERE source_reference = :reference_code
            )
            """
        ),
        {"reference_code": cancelled_reference_code},
    )
    assert remaining_pending_identifiers == 0
