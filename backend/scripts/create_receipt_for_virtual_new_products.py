from __future__ import annotations

import asyncio
import json
from uuid import uuid4

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
REFERENCE_CODE = "NK20260624-BO-SUNG-TON-MOI"
PRODUCT_CREATED_SINCE = "2026-06-23"


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    before_total = await conn.fetchval("SELECT COALESCE(SUM(on_hand_quantity), 0) FROM inventory_levels")
    try:
        async with conn.transaction():
            existing = await conn.fetchrow(
                "SELECT id, status FROM inventory_documents WHERE document_no = $1",
                REFERENCE_CODE,
            )
            if existing:
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "skipped": True,
                            "reason": "receipt_exists",
                            "referenceCode": REFERENCE_CODE,
                            "status": existing["status"],
                        },
                        ensure_ascii=False,
                    )
                )
                return

            admin_user_id = await conn.fetchval(
                "SELECT id FROM users WHERE lower(email) = 'admin@admin.com' AND deleted_at IS NULL LIMIT 1"
            )
            rows = await conn.fetch(
                """
                WITH inbound AS (
                    SELECT
                        l.variant_id,
                        l.location_id,
                        SUM(COALESCE((l.metadata->>'receivedQuantity')::int, l.requested_quantity, 0)) AS quantity
                    FROM inventory_document_lines l
                    JOIN inventory_documents d ON d.id = l.document_id
                    WHERE d.document_type = 'INBOUND'
                      AND d.status = 'COMPLETED'
                    GROUP BY l.variant_id, l.location_id
                )
                SELECT
                    p.id AS product_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    v.id AS variant_id,
                    v.sku AS variant_sku,
                    il.location_id,
                    loc.code AS location_code,
                    loc.name AS location_name,
                    il.on_hand_quantity,
                    NULLIF(il.average_unit_cost, 0) AS unit_cost
                FROM inventory_levels il
                JOIN product_variants v ON v.id = il.variant_id
                JOIN products p ON p.id = v.product_id
                JOIN inventory_locations loc ON loc.id = il.location_id
                LEFT JOIN inbound i ON i.variant_id = il.variant_id AND i.location_id = il.location_id
                WHERE il.on_hand_quantity > 0
                  AND COALESCE(i.quantity, 0) = 0
                  AND p.deleted_at IS NULL
                  AND p.status = 'ACTIVE'
                  AND p.created_at >= ($1::text)::timestamptz
                ORDER BY p.created_at, p.name, v.sku
                """,
                PRODUCT_CREATED_SINCE,
            )
            if not rows:
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "skipped": True,
                            "reason": "no_virtual_new_stock",
                            "referenceCode": REFERENCE_CODE,
                        },
                        ensure_ascii=False,
                    )
                )
                return

            document_id = uuid4()
            total_quantity = sum(int(row["on_hand_quantity"]) for row in rows)
            target_location_id = rows[0]["location_id"]
            metadata = {
                "qualityStatus": "PASSED",
                "qualityLabel": "Đạt",
                "qualityNote": "Đối soát tồn đã nhập từ dữ liệu seed sản phẩm mới.",
                "quarantine": False,
                "quarantineLocation": None,
                "reconcilesExistingStock": True,
                "stockMutationSkipped": True,
                "productCreatedSince": PRODUCT_CREATED_SINCE,
                "lineCount": len(rows),
                "totalQuantity": total_quantity,
            }
            await conn.execute(
                """
                INSERT INTO inventory_documents (
                    id, document_no, document_type, status, target_location_id,
                    supplier_name, reference_code, reason, note,
                    created_by, approved_by, posted_by,
                    approved_at, posted_at, metadata
                )
                VALUES (
                    $1, $2, 'INBOUND', 'COMPLETED', $3,
                    $4, $2, 'NK_BO_SUNG_TON_MOI', $5,
                    $6, $6, $6,
                    NOW(), NOW(), $7::jsonb
                )
                """,
                document_id,
                REFERENCE_CODE,
                target_location_id,
                "Bổ sung chứng từ nhập kho",
                "Phiếu nhập bổ sung để hợp thức hóa tồn hiện có của nhóm sản phẩm mới; không cộng tồn thêm lần nữa.",
                admin_user_id,
                json.dumps(metadata, ensure_ascii=False),
            )

            for row in rows:
                quantity = int(row["on_hand_quantity"])
                line_id = uuid4()
                line_metadata = {
                    "imeis": [],
                    "tracksImei": False,
                    "serialNumbers": [],
                    "tracksSerialNumber": False,
                    "plannedQuantity": quantity,
                    "receivedQuantity": quantity,
                    "storageLocationCode": row["location_code"],
                    "storageLocationName": row["location_name"],
                    "reconcilesExistingStock": True,
                    "stockMutationSkipped": True,
                }
                await conn.execute(
                    """
                    INSERT INTO inventory_document_lines (
                        id, document_id, product_id, variant_id, location_id,
                        requested_quantity, approved_quantity, expected_quantity,
                        unit_cost, note, metadata
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $6, $6, $7, $8, $9::jsonb)
                    """,
                    line_id,
                    document_id,
                    row["product_id"],
                    row["variant_id"],
                    row["location_id"],
                    quantity,
                    row["unit_cost"],
                    "Dòng nhập bổ sung từ tồn hiện có, không thay đổi số lượng kho.",
                    json.dumps(line_metadata, ensure_ascii=False),
                )

                lot_id = uuid4()
                lot_code = f"LOT-{REFERENCE_CODE}-{str(lot_id)[:8]}".upper()
                await conn.execute(
                    """
                    INSERT INTO inventory_lots (
                        id, lot_code, product_id, variant_id, location_id,
                        source_document_id, source_reference,
                        initial_quantity, remaining_quantity, unit_cost,
                        received_at, status, metadata
                    )
                    VALUES (
                        $1, $2, NULL, $3, $4,
                        $5, $6,
                        $7, $7, $8,
                        NOW(), 'ACTIVE', $9::jsonb
                    )
                    """,
                    lot_id,
                    lot_code,
                    row["variant_id"],
                    row["location_id"],
                    document_id,
                    REFERENCE_CODE,
                    quantity,
                    row["unit_cost"],
                    json.dumps(
                        {
                            "reconcilesExistingStock": True,
                            "stockMutationSkipped": True,
                            "productSku": row["product_sku"],
                            "variantSku": row["variant_sku"],
                        },
                        ensure_ascii=False,
                    ),
                )
                await conn.execute(
                    """
                    INSERT INTO inventory_lot_movements (
                        id, lot_id, movement_type, quantity,
                        reference_code, inventory_document_id, note
                    )
                    VALUES ($1, $2, 'RECEIPT', $3, $4, $5, $6)
                    """,
                    uuid4(),
                    lot_id,
                    quantity,
                    REFERENCE_CODE,
                    document_id,
                    "Tạo lô bổ sung khi đối soát tồn hiện có, không cộng tồn thêm.",
                )
                await conn.execute(
                    """
                    INSERT INTO inventory_adjustment_logs (
                        id, product_id, variant_id, old_quantity, new_quantity,
                        delta, reason, note, supplier_name, unit_cost,
                        location_code, location_name, reference_code, transaction_type
                    )
                    VALUES (
                        $1, $2, $3, 0, $4,
                        $4, 'NK_BO_SUNG_TON_MOI', $5, $6, $7,
                        $8, $9, $10, 'RECEIPT'
                    )
                    """,
                    uuid4(),
                    row["product_id"],
                    row["variant_id"],
                    quantity,
                    "Log nhập kho bổ sung cho tồn đã có sẵn từ dữ liệu sản phẩm mới; script không cập nhật lại tồn.",
                    "Bổ sung chứng từ nhập kho",
                    row["unit_cost"],
                    row["location_code"],
                    row["location_name"],
                    REFERENCE_CODE,
                )

            await conn.execute(
                """
                INSERT INTO security_audit_logs (user_id, event_type, ip_address, user_agent, metadata)
                VALUES ($1, 'inventory_receipt_reconciled_virtual_stock', 'system', NULL, $2::jsonb)
                """,
                admin_user_id,
                json.dumps(
                    {
                        "referenceCode": REFERENCE_CODE,
                        "lineCount": len(rows),
                        "totalQuantity": total_quantity,
                        "productCreatedSince": PRODUCT_CREATED_SINCE,
                        "stockMutationSkipped": True,
                    },
                    ensure_ascii=False,
                ),
            )

        after_total = await conn.fetchval("SELECT COALESCE(SUM(on_hand_quantity), 0) FROM inventory_levels")
        created = await conn.fetchrow(
            """
            SELECT
                d.document_no,
                d.status,
                COUNT(l.id) AS line_count,
                COALESCE(SUM(l.requested_quantity), 0) AS total_quantity
            FROM inventory_documents d
            JOIN inventory_document_lines l ON l.document_id = d.id
            WHERE d.document_no = $1
            GROUP BY d.document_no, d.status
            """,
            REFERENCE_CODE,
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "referenceCode": REFERENCE_CODE,
                    "status": created["status"],
                    "lineCount": int(created["line_count"]),
                    "totalQuantity": int(created["total_quantity"]),
                    "inventoryBefore": int(before_total),
                    "inventoryAfter": int(after_total),
                    "inventoryChanged": int(after_total) - int(before_total),
                },
                ensure_ascii=False,
            )
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
