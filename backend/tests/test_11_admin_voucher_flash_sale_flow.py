import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text


def _voucher_payload(code: str, *, status: str = "ACTIVE") -> dict:
    return {
        "code": code,
        "discountType": "FIXED",
        "discountAmount": 50000,
        "minOrderValue": 100000,
        "usageLimit": 10,
        "perUserLimit": 1,
        "campaignType": "CONVERSION",
        "audienceType": "PUBLIC",
        "displayTitle": "Voucher kiểm thử admin",
        "displayDescription": "Voucher chỉ dùng trong database kiểm thử",
        "applicableChannels": ["WEB"],
        "applicablePaymentMethods": ["COD"],
        "refundPolicy": "SHOP_FAULT_ONLY",
        "status": status,
    }


async def _create_product_variant(db_session):
    product_id = uuid4()
    variant_id = uuid4()
    sku = f"TEST-FS-{uuid4().hex[:8].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'ACCESSORY', 'Thương hiệu kiểm thử',
                1000000, 1000000, 5, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Sản phẩm flash sale kiểm thử",
            "slug": f"san-pham-flash-sale-{uuid4().hex[:8]}",
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
                1000000, 1000000, 5, TRUE
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
    return product_id, variant_id


@pytest.mark.workflow
async def test_admin_voucher_crud_and_permission_guards(
    api_client,
    db_session,
    admin_headers,
    customer_headers,
):
    code = f"ADMINTEST{uuid4().hex[:8].upper()}"
    payload = _voucher_payload(code)

    forbidden = await api_client.post(
        "/api/admin/vouchers",
        headers=customer_headers,
        json=payload,
    )
    assert forbidden.status_code == 403, forbidden.text

    invalid = await api_client.post(
        "/api/admin/vouchers",
        headers=admin_headers,
        json={**payload, "discountAmount": -1},
    )
    assert invalid.status_code == 422, invalid.text

    created = await api_client.post(
        "/api/admin/vouchers",
        headers=admin_headers,
        json=payload,
    )
    assert created.status_code == 201, created.text
    voucher_id = created.json()["id"]

    listed = await api_client.get("/api/admin/vouchers", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    assert code in listed.text

    updated = await api_client.patch(
        f"/api/admin/vouchers/{voucher_id}",
        headers=admin_headers,
        json=_voucher_payload(code, status="INACTIVE"),
    )
    assert updated.status_code == 200, updated.text

    status = await db_session.scalar(
        text("SELECT status FROM vouchers WHERE id = :voucher_id"),
        {"voucher_id": voucher_id},
    )
    assert status == "INACTIVE"

    deleted = await api_client.delete(
        f"/api/admin/vouchers/{voucher_id}",
        headers=admin_headers,
    )
    assert deleted.status_code == 200, deleted.text

    deleted_status = await db_session.scalar(
        text("SELECT status FROM vouchers WHERE id = :voucher_id"),
        {"voucher_id": voucher_id},
    )
    assert deleted_status == "INACTIVE"


@pytest.mark.workflow
async def test_admin_flash_sale_create_overlap_delete_and_permission_guards(
    api_client,
    db_session,
    admin_headers,
    customer_headers,
):
    product_id, variant_id = await _create_product_variant(db_session)
    starts_at = datetime.now(UTC) + timedelta(hours=1)
    ends_at = starts_at + timedelta(hours=2)
    payload = {
        "productId": str(product_id),
        "variantId": str(variant_id),
        "discountType": "PERCENT",
        "discountValue": 10,
        "quantityLimit": 3,
        "startsAt": starts_at.isoformat(),
        "endsAt": ends_at.isoformat(),
        "status": "ACTIVE",
    }

    forbidden = await api_client.post(
        "/api/admin/flash-sales",
        headers=customer_headers,
        json=payload,
    )
    assert forbidden.status_code == 403, forbidden.text

    invalid = await api_client.post(
        "/api/admin/flash-sales",
        headers=admin_headers,
        json={**payload, "discountValue": 100},
    )
    assert invalid.status_code == 422, invalid.text

    created = await api_client.post(
        "/api/admin/flash-sales",
        headers=admin_headers,
        json=payload,
    )
    assert created.status_code == 201, created.text
    sale_id = created.json()["id"]

    overlap = await api_client.post(
        "/api/admin/flash-sales",
        headers=admin_headers,
        json=payload,
    )
    assert overlap.status_code == 409, overlap.text

    listed = await api_client.get("/api/admin/flash-sales", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    assert sale_id in listed.text
    listed_sale = next(item for item in listed.json() if item["id"] == sale_id)
    assert listed_sale["quantityLimit"] == 3
    assert listed_sale["soldQuantity"] == 0
    assert listed_sale["remainingQuantity"] == 3
    assert listed_sale["isLimited"] is True

    deleted = await api_client.delete(
        f"/api/admin/flash-sales/{sale_id}",
        headers=admin_headers,
    )
    assert deleted.status_code == 200, deleted.text

    remaining = await db_session.scalar(
        text("SELECT COUNT(*) FROM flash_sales WHERE id = :sale_id"),
        {"sale_id": sale_id},
    )
    assert remaining == 0
