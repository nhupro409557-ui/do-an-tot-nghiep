import json
from uuid import uuid4

import pytest
from sqlalchemy import text


async def _create_supplier(api_client, admin_headers, name: str) -> str:
    code = f"NCC-CN-{uuid4().hex[:8].upper()}"
    response = await api_client.post(
        "/api/admin/suppliers",
        headers=admin_headers,
        json={
            "name": name,
            "code": code,
            "email": f"{code.lower()}@example.com",
            "isActive": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _create_product_with_variant(db_session, *, sku_prefix: str = "CN") -> tuple[str, str, str]:
    product_id = uuid4()
    variant_id = uuid4()
    sku = f"TEST-{sku_prefix}-{uuid4().hex[:8].upper()}"
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
            "name": "Sản phẩm kiểm thử công nợ",
            "slug": f"san-pham-cong-no-{uuid4().hex[:8]}",
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
    return str(product_id), str(variant_id), sku


@pytest.mark.contract
async def test_supplier_profile_rejects_duplicate_name(api_client, admin_headers):
    supplier_name = f"Nhà cung cấp trùng hồ sơ {uuid4().hex[:8]}"
    first_id = await _create_supplier(api_client, admin_headers, supplier_name)
    assert first_id

    duplicate = await api_client.post(
        "/api/admin/suppliers",
        headers=admin_headers,
        json={
            "name": supplier_name,
            "code": f"NCC-DUP-{uuid4().hex[:8].upper()}",
            "email": f"dup-{uuid4().hex[:8]}@example.com",
            "isActive": True,
        },
    )
    assert duplicate.status_code == 409, duplicate.text
    assert "Tên nhà cung cấp" in duplicate.text


@pytest.mark.contract
async def test_supplier_profile_rejects_duplicate_code(api_client, admin_headers):
    supplier_code = f"NCC-CODE-DUP-{uuid4().hex[:8].upper()}"
    first = await api_client.post(
        "/api/admin/suppliers",
        headers=admin_headers,
        json={
            "name": f"NCC Thử trùng mã 1 {uuid4().hex[:8]}",
            "code": supplier_code,
            "email": f"code1-{uuid4().hex[:8]}@example.com",
            "isActive": True,
        },
    )
    assert first.status_code == 201

    duplicate = await api_client.post(
        "/api/admin/suppliers",
        headers=admin_headers,
        json={
            "name": f"NCC Thử trùng mã 2 {uuid4().hex[:8]}",
            "code": supplier_code,
            "email": f"code2-{uuid4().hex[:8]}@example.com",
            "isActive": True,
        },
    )
    assert duplicate.status_code == 409, duplicate.text
    assert "Mã nhà cung cấp" in duplicate.text


@pytest.mark.contract
async def test_supplier_profile_rejects_duplicate_tax_code(api_client, admin_headers):
    tax_code = f"TAX-{uuid4().hex[:8].upper()}"
    first = await api_client.post(
        "/api/admin/suppliers",
        headers=admin_headers,
        json={
            "name": f"NCC Thử trùng MST 1 {uuid4().hex[:8]}",
            "code": f"NCC-TAX1-{uuid4().hex[:8].upper()}",
            "taxCode": tax_code,
            "isActive": True,
        },
    )
    assert first.status_code == 201

    duplicate = await api_client.post(
        "/api/admin/suppliers",
        headers=admin_headers,
        json={
            "name": f"NCC Thử trùng MST 2 {uuid4().hex[:8]}",
            "code": f"NCC-TAX2-{uuid4().hex[:8].upper()}",
            "taxCode": tax_code,
            "isActive": True,
        },
    )
    assert duplicate.status_code == 409, duplicate.text
    assert "Mã số thuế" in duplicate.text


@pytest.mark.contract
async def test_supplier_profile_validation_errors(api_client, admin_headers):
    # Invalid Email
    res_email = await api_client.post(
        "/api/admin/suppliers",
        headers=admin_headers,
        json={
            "name": "NCC Invalid Email",
            "code": f"NCC-EV-{uuid4().hex[:8].upper()}",
            "email": "not-an-email",
            "isActive": True,
        },
    )
    assert res_email.status_code == 400
    assert "Email không hợp lệ" in res_email.text

    # Invalid SĐT
    res_phone = await api_client.post(
        "/api/admin/suppliers",
        headers=admin_headers,
        json={
            "name": "NCC Invalid Phone",
            "code": f"NCC-PV-{uuid4().hex[:8].upper()}",
            "phone": "12345",
            "isActive": True,
        },
    )
    assert res_phone.status_code == 400
    assert "Số điện thoại không hợp lệ" in res_phone.text

    # Too short name
    res_name = await api_client.post(
        "/api/admin/suppliers",
        headers=admin_headers,
        json={
            "name": "A",
            "code": f"NCC-NV-{uuid4().hex[:8].upper()}",
            "isActive": True,
        },
    )
    assert res_name.status_code == 400
    assert "Tên nhà cung cấp phải từ 2 đến 200 ký tự" in res_name.text


async def _complete_receipt(
    api_client,
    admin_headers,
    approver_headers,
    *,
    supplier_id: str,
    supplier_name: str,
    product_id: str,
    variant_id: str,
    quantity: int,
    unit_cost: int,
    payment_term_days: int = 15,
    due_date: str | None = None,
    paid_amount: int = 0,
) -> str:
    reference_code = f"TEST-CN-{uuid4().hex[:10].upper()}"
    payload = {
        "referenceCode": reference_code,
        "receiptReasonCode": "NK_MUA",
        "supplierId": supplier_id,
        "supplierName": supplier_name,
        "invoiceNumber": f"INV-{uuid4().hex[:8].upper()}",
        "paymentMode": "DEBT",
        "paymentTermDays": payment_term_days,
        "paidAmount": paid_amount,
        "qualityStatus": "PASSED",
        "status": "DRAFT",
        "lines": [
            {
                "productId": product_id,
                "variantId": variant_id,
                "quantity": quantity,
                "unitCost": unit_cost,
                "storageLocationCode": "A-01-01",
            }
        ],
    }
    if due_date:
        payload["dueDate"] = due_date
    created = await api_client.post(
        "/api/admin/inventory/receipts",
        headers={**admin_headers, "Idempotency-Key": reference_code},
        json=payload,
    )
    assert created.status_code == 200, created.text

    for target_status in ("APPROVED", "COMPLETED"):
        changed = await api_client.patch(
            f"/api/admin/inventory/receipts/{reference_code}/status",
            headers=approver_headers,
            json={"status": target_status},
        )
        assert changed.status_code == 200, f"{target_status}: {changed.status_code} {changed.text}"
    return reference_code


@pytest.mark.workflow
async def test_supplier_account_payable_created_from_completed_receipt_and_paid_partially(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    supplier_name = "Nhà cung cấp công nợ kiểm thử"
    supplier_id = await _create_supplier(api_client, admin_headers, supplier_name)
    product_id, variant_id, _sku = await _create_product_with_variant(db_session)
    reference_code = await _complete_receipt(
        api_client,
        admin_headers,
        approver_headers,
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        product_id=product_id,
        variant_id=variant_id,
        quantity=4,
        unit_cost=250000,
        payment_term_days=10,
    )

    payable = (
        await db_session.execute(
            text(
                """
                SELECT id::text, supplier_id::text, principal_amount, paid_amount, remaining_amount, status
                FROM account_payables
                WHERE source_reference_code = :reference_code
                """
            ),
            {"reference_code": reference_code},
        )
    ).mappings().one()
    assert payable["supplier_id"] == supplier_id
    assert float(payable["principal_amount"]) == 1_000_000
    assert float(payable["paid_amount"]) == 0
    assert float(payable["remaining_amount"]) == 1_000_000
    assert payable["status"] == "OPEN"

    listed = await api_client.get(
        "/api/admin/account-payables",
        headers=admin_headers,
        params={"search": reference_code},
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"][0]["sourceReferenceCode"] == reference_code

    overpay = await api_client.post(
        f"/api/admin/account-payables/{payable['id']}/payments",
        headers=admin_headers,
        json={"amount": 1_000_001, "method": "BANK_TRANSFER"},
    )
    assert overpay.status_code == 400, overpay.text

    partial = await api_client.post(
        f"/api/admin/account-payables/{payable['id']}/payments",
        headers=admin_headers,
        json={"amount": 400000, "method": "BANK_TRANSFER", "referenceNo": "UNC-TEST-01"},
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["status"] == "PARTIAL"
    assert float(partial.json()["remainingAmount"]) == 600000

    rest = await api_client.post(
        f"/api/admin/account-payables/{payable['id']}/payments",
        headers=admin_headers,
        json={"amount": 600000, "method": "CASH", "referenceNo": "TM-TEST-02"},
    )
    assert rest.status_code == 200, rest.text
    assert rest.json()["status"] == "PAID"
    assert float(rest.json()["remainingAmount"]) == 0

    detail = await api_client.get(f"/api/admin/account-payables/{payable['id']}", headers=admin_headers)
    assert detail.status_code == 200, detail.text
    detail_payload = detail.json()
    assert detail_payload["status"] == "PAID"
    assert len(detail_payload["payments"]) == 2

    delete_supplier = await api_client.delete(f"/api/admin/suppliers/{supplier_id}", headers=admin_headers)
    assert delete_supplier.status_code == 409, delete_supplier.text
    assert "ẩn nhà cung cấp" in delete_supplier.text


@pytest.mark.workflow
async def test_supplier_account_payable_overdue_filter_and_receipt_reversal_cancel(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    supplier_name = "Nhà cung cấp quá hạn kiểm thử"
    supplier_id = await _create_supplier(api_client, admin_headers, supplier_name)
    product_id, variant_id, _sku = await _create_product_with_variant(db_session, sku_prefix="CNQH")
    reference_code = await _complete_receipt(
        api_client,
        admin_headers,
        approver_headers,
        supplier_id=supplier_id,
        supplier_name=supplier_name,
        product_id=product_id,
        variant_id=variant_id,
        quantity=2,
        unit_cost=300000,
        due_date="2000-01-01T00:00:00Z",
    )

    overdue = await api_client.get(
        "/api/admin/account-payables",
        headers=admin_headers,
        params={"status": "OVERDUE", "search": reference_code},
    )
    assert overdue.status_code == 200, overdue.text
    assert overdue.json()["items"][0]["status"] == "OVERDUE"
    payable_id = overdue.json()["items"][0]["id"]

    reversed_receipt = await api_client.post(
        f"/api/admin/inventory/receipts/{reference_code}/reverse",
        headers=approver_headers,
        json={"reason": "Hủy công nợ kiểm thử", "note": "Đảo phiếu để kiểm tra hủy công nợ."},
    )
    assert reversed_receipt.status_code == 200, reversed_receipt.text

    detail = await api_client.get(f"/api/admin/account-payables/{payable_id}", headers=admin_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "CANCELLED"
    assert float(detail.json()["remainingAmount"]) == 0


@pytest.mark.workflow
async def test_supplier_account_payable_rejects_receipt_paid_amount_above_principal(
    api_client,
    db_session,
    admin_headers,
    approver_headers,
):
    supplier_name = "Nhà cung cấp trả trước vượt giá trị kiểm thử"
    supplier_id = await _create_supplier(api_client, admin_headers, supplier_name)
    product_id, variant_id, _sku = await _create_product_with_variant(db_session, sku_prefix="CNTT")
    reference_code = f"TEST-CN-OVERPAID-{uuid4().hex[:8].upper()}"
    payload = {
        "referenceCode": reference_code,
        "receiptReasonCode": "NK_MUA",
        "supplierId": supplier_id,
        "supplierName": supplier_name,
        "invoiceNumber": f"INV-{uuid4().hex[:8].upper()}",
        "paymentMode": "DEBT",
        "paymentTermDays": 15,
        "paidAmount": 1_200_000,
        "qualityStatus": "PASSED",
        "status": "DRAFT",
        "lines": [
            {
                "productId": product_id,
                "variantId": variant_id,
                "quantity": 2,
                "unitCost": 500_000,
                "storageLocationCode": "A-01-01",
            }
        ],
    }
    created = await api_client.post(
        "/api/admin/inventory/receipts",
        headers={**admin_headers, "Idempotency-Key": reference_code},
        json=payload,
    )
    assert created.status_code == 200, created.text

    approved = await api_client.patch(
        f"/api/admin/inventory/receipts/{reference_code}/status",
        headers=approver_headers,
        json={"status": "APPROVED"},
    )
    assert approved.status_code == 200, approved.text

    completed = await api_client.patch(
        f"/api/admin/inventory/receipts/{reference_code}/status",
        headers=approver_headers,
        json={"status": "COMPLETED"},
    )
    assert completed.status_code == 400, completed.text
    assert "trả trước" in completed.text

    payable_count = await db_session.scalar(
        text("SELECT COUNT(*) FROM account_payables WHERE source_reference_code = :reference_code"),
        {"reference_code": reference_code},
    )
    receipt_status = await db_session.scalar(
        text("SELECT status FROM inventory_documents WHERE document_no = :reference_code"),
        {"reference_code": reference_code},
    )
    variant_stock = await db_session.scalar(
        text("SELECT stock_quantity FROM product_variants WHERE id = :variant_id"),
        {"variant_id": variant_id},
    )
    assert payable_count == 0
    assert receipt_status == "APPROVED"
    assert variant_stock == 0
