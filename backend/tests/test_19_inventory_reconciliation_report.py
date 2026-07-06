import json
from uuid import uuid4

import pytest
from sqlalchemy import text


def _imei(prefix: str = "35") -> str:
    return (prefix + str(uuid4().int))[:15]


@pytest.mark.workflow
async def test_inventory_reconciliation_report_detects_level_identifier_mismatches(
    api_client,
    db_session,
    admin_headers,
):
    product_id = uuid4()
    variant_id = uuid4()
    location_id = uuid4()
    orphan_location_id = uuid4()
    sku = f"RECON-{uuid4().hex[:8].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'PHONE', 'Thương hiệu kiểm thử',
                12000000, 12000000, 2, 'ACTIVE', CAST(:sales_config AS JSONB)
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Sản phẩm đối soát tồn kiểm thử",
            "slug": f"san-pham-doi-soat-ton-{uuid4().hex[:8]}",
            "sales_config": json.dumps(
                {
                    "imeiPolicy": {"mode": "MANUAL", "trackImei": True},
                    "serialPolicy": {"mode": "MANUAL", "trackSerialNumber": True},
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
                12000000, 12000000, 2, TRUE
            )
            """
        ),
        {
            "variant_id": variant_id,
            "product_id": product_id,
            "variant_sku": f"{sku}-DEFAULT",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_locations (id, code, name, location_type, status, is_default)
            VALUES
                (:location_id, :location_code, 'Kệ đối soát kiểm thử', 'WAREHOUSE', 'ACTIVE', FALSE),
                (:orphan_location_id, :orphan_location_code, 'Kệ mã lệch kiểm thử', 'WAREHOUSE', 'ACTIVE', FALSE)
            """
        ),
        {
            "location_id": location_id,
            "location_code": f"R-{uuid4().hex[:6].upper()}",
            "orphan_location_id": orphan_location_id,
            "orphan_location_code": f"R-{uuid4().hex[:6].upper()}",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_levels (
                id, product_id, variant_id, location_id,
                on_hand_quantity, reserved_quantity, average_unit_cost
            )
            VALUES (gen_random_uuid(), NULL, :variant_id, :location_id, 2, 0, 9000000)
            """
        ),
        {"variant_id": variant_id, "location_id": location_id},
    )
    in_stock_with_location = _imei("35")
    in_stock_without_location = _imei("86")
    sold_with_location = _imei("99")
    await db_session.execute(
        text(
            """
            INSERT INTO product_imeis (
                id, product_id, variant_id, imei, status,
                location_id, source_reference, is_primary
            )
            VALUES
                (gen_random_uuid(), :product_id, :variant_id, :in_stock_with_location, 'IN_STOCK', :location_id, :source_reference, TRUE),
                (gen_random_uuid(), :product_id, :variant_id, :in_stock_without_location, 'IN_STOCK', NULL, :source_reference, FALSE),
                (gen_random_uuid(), :product_id, :variant_id, :sold_with_location, 'SOLD', :location_id, :source_reference, FALSE)
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "in_stock_with_location": in_stock_with_location,
            "in_stock_without_location": in_stock_without_location,
            "sold_with_location": sold_with_location,
            "location_id": location_id,
            "source_reference": f"RECEIPT-{sku}",
        },
    )
    serial_without_level = f"SN{uuid4().hex[:12].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (
                id, product_id, variant_id, serial_number, status,
                location_id, source_reference
            )
            VALUES (
                gen_random_uuid(), :product_id, :variant_id, :serial_number, 'IN_STOCK',
                :orphan_location_id, :source_reference
            )
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "serial_number": serial_without_level,
            "orphan_location_id": orphan_location_id,
            "source_reference": f"RECEIPT-{sku}",
        },
    )
    await db_session.commit()

    response = await api_client.get(
        f"/api/admin/inventory/reports/reconciliation?search={sku}",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    issue_types = {item["issueType"] for item in payload["items"]}
    assert "LEVEL_GT_IDENTIFIERS" in issue_types
    assert "IDENTIFIER_IN_STOCK_WITHOUT_LOCATION" in issue_types
    assert "IDENTIFIER_LOCATION_WITHOUT_LEVEL" in issue_types
    assert "TERMINAL_IDENTIFIER_WITH_LOCATION" in issue_types

    summary = {item["issueType"]: item["count"] for item in payload["summary"]}
    assert summary["LEVEL_GT_IDENTIFIERS"] == 1
    assert summary["IDENTIFIER_IN_STOCK_WITHOUT_LOCATION"] == 1
    assert summary["IDENTIFIER_LOCATION_WITHOUT_LEVEL"] == 1
    assert summary["TERMINAL_IDENTIFIER_WITH_LOCATION"] == 1

    filtered = await api_client.get(
        f"/api/admin/inventory/reports/reconciliation?search={sku}&issueType=TERMINAL_IDENTIFIER_WITH_LOCATION",
        headers=admin_headers,
    )
    assert filtered.status_code == 200, filtered.text
    filtered_payload = filtered.json()
    assert filtered_payload["totalIssues"] == 1
    assert filtered_payload["items"][0]["identifierValue"] == sold_with_location


@pytest.mark.workflow
async def test_advanced_inventory_reconciliation_report_mismatches(
    api_client,
    db_session,
    admin_headers,
):
    product_id = uuid4()
    variant_id = uuid4()
    location_id = uuid4()
    sku = f"ADV-RECON-{uuid4().hex[:8].upper()}"

    # 1. Product with mismatched sellable stock
    await db_session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, price, sale_price,
                stock_quantity, status, sales_config
            )
            VALUES (
                :id, :sku, :name, :slug, 'PHONE', 'Thương hiệu đối soát',
                15000000, 15000000, 10, 'ACTIVE', '{}'::jsonb
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": "Sản phẩm đối soát nâng cao",
            "slug": f"san-pham-doi-soat-nang-cao-{uuid4().hex[:8]}",
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
                15000000, 15000000, 10, TRUE
            )
            """
        ),
        {
            "variant_id": variant_id,
            "product_id": product_id,
            "variant_sku": f"{sku}-DEFAULT",
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_locations (id, code, name, location_type, status, purpose, is_default)
            VALUES (:location_id, :location_code, 'Kệ đối soát nâng cao', 'WAREHOUSE', 'ACTIVE', 'STORAGE', FALSE)
            """
        ),
        {
            "location_id": location_id,
            "location_code": f"ADV-{uuid4().hex[:5].upper()}",
        },
    )
    # Total sellable stock on STORAGE shelf = 3 (on_hand_quantity = 3, reserved = 0)
    # But product_variants.stock_quantity = 10 -> SELLABLE_STOCK_MISMATCH!
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_levels (
                id, product_id, variant_id, location_id,
                on_hand_quantity, reserved_quantity, average_unit_cost
            )
            VALUES (gen_random_uuid(), NULL, :variant_id, :location_id, 3, 2, 9000000)
            """
        ),
        {"variant_id": variant_id, "location_id": location_id},
    )
    # Wait, reserved_quantity = 2 on shelf, but no RESERVED identifiers -> RESERVED_QUANTITY_MISMATCH!

    # 2. Lot mismatch: remaining_quantity in lots = 1, but level.on_hand_quantity = 3 -> LOT_QUANTITY_MISMATCH!
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_lots (
                id, lot_code, product_id, variant_id, location_id,
                initial_quantity, remaining_quantity, status
            )
            VALUES (
                gen_random_uuid(), :lot_code, NULL, :variant_id, :location_id,
                1, 1, 'ACTIVE'
            )
            """
        ),
        {
            "lot_code": f"LOT-{uuid4().hex[:6].upper()}",
            "variant_id": variant_id,
            "location_id": location_id,
        },
    )

    # 3. Pair mismatch: pair created but IMEI/Serial have different locations -> IDENTIFIER_PAIR_MISMATCH!
    imei_pair = _imei("35")
    serial_pair = f"SN-PAIR-{uuid4().hex[:8].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO product_imeis (id, product_id, variant_id, imei, status, location_id)
            VALUES (gen_random_uuid(), :product_id, :variant_id, :imei, 'IN_STOCK', :location_id)
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "imei": imei_pair,
            "location_id": location_id,
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_serial_numbers (id, product_id, variant_id, serial_number, status, location_id)
            VALUES (gen_random_uuid(), :product_id, :variant_id, :serial_number, 'IN_STOCK', NULL)
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "serial_number": serial_pair,
        },
    )
    await db_session.execute(
        text(
            """
            INSERT INTO product_identifier_pairs (id, product_id, variant_id, imei1, serial_number)
            VALUES (gen_random_uuid(), :product_id, :variant_id, :imei1, :serial_number)
            """
        ),
        {
            "product_id": product_id,
            "variant_id": variant_id,
            "imei1": imei_pair,
            "serial_number": serial_pair,
        },
    )

    # 4. Document mismatch: completed document without adjustment logs -> DOCUMENT_LEDGER_MISMATCH!
    doc_no = f"NK-MISMATCH-{uuid4().hex[:6].upper()}"
    await db_session.execute(
        text(
            """
            INSERT INTO inventory_documents (
                id, document_no, document_type, status, reason, created_by
            )
            VALUES (gen_random_uuid(), :doc_no, 'INBOUND', 'COMPLETED', 'NHAP_KHO', NULL)
            """
        ),
        {"doc_no": doc_no},
    )
    await db_session.commit()

    # Query the report
    res = await api_client.get(
        "/api/admin/inventory/reports/reconciliation",
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    issue_types = {item["issueType"] for item in payload["items"]}

    assert "SELLABLE_STOCK_MISMATCH" in issue_types
    assert "LOT_QUANTITY_MISMATCH" in issue_types
    assert "RESERVED_QUANTITY_MISMATCH" in issue_types
    assert "IDENTIFIER_PAIR_MISMATCH" in issue_types
    assert "DOCUMENT_LEDGER_MISMATCH" in issue_types
