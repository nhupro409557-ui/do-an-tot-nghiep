from __future__ import annotations

import asyncio
import json
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
REFERENCE_CODE = "NK20260624-BO-SUNG-TON-MOI"
ACCESSORY_TARGET_QUANTITY = 45
DEFAULT_TARGET_QUANTITY = 12


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def is_technology_accessory(category: str, subcategory: str) -> bool:
    text = f"{category} {subcategory}".lower()
    return "phụ kiện công nghệ" in text or "phụ kiện" in text


def target_quantity(category: str, subcategory: str) -> int:
    if is_technology_accessory(category, subcategory):
        return ACCESSORY_TARGET_QUANTITY
    return DEFAULT_TARGET_QUANTITY


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        async with conn.transaction():
            document = await conn.fetchrow(
                """
                SELECT id, status
                FROM inventory_documents
                WHERE document_no = $1
                FOR UPDATE
                """,
                REFERENCE_CODE,
            )
            if not document:
                raise RuntimeError(f"Không tìm thấy phiếu {REFERENCE_CODE}.")
            if document["status"] != "COMPLETED":
                raise RuntimeError(
                    f"Phiếu {REFERENCE_CODE} đang ở trạng thái {document['status']}, không phải COMPLETED."
                )

            rows = await conn.fetch(
                """
                SELECT
                    l.id AS line_id,
                    l.metadata,
                    l.product_id,
                    l.variant_id,
                    l.location_id,
                    l.requested_quantity AS old_quantity,
                    COALESCE(cat.name, '') AS category_name,
                    COALESCE(subcat.name, '') AS subcategory_name,
                    COALESCE(NULLIF(pv.sale_price, 0), NULLIF(pv.price, 0), NULLIF(p.sale_price, 0), p.price, 0)::numeric AS current_sale_price,
                    il.id AS level_id,
                    lot.id AS lot_id
                FROM inventory_document_lines l
                JOIN products p ON p.id = l.product_id
                LEFT JOIN product_variants pv ON pv.id = l.variant_id
                LEFT JOIN categories cat ON cat.id = p.category_id
                LEFT JOIN categories subcat ON subcat.id = p.subcategory_id
                LEFT JOIN inventory_levels il ON il.variant_id = l.variant_id AND il.location_id = l.location_id
                LEFT JOIN inventory_lots lot ON lot.source_document_id = l.document_id AND lot.variant_id = l.variant_id
                WHERE l.document_id = $1
                ORDER BY cat.name, subcat.name, p.name, pv.sku
                FOR UPDATE OF l
                """,
                document["id"],
            )
            if not rows:
                raise RuntimeError(f"Phiếu {REFERENCE_CODE} không có dòng sản phẩm.")

            changed_variants: list[dict] = []
            affected_product_ids: set[str] = set()
            for row in rows:
                quantity = target_quantity(row["category_name"], row["subcategory_name"])
                old_quantity = int(row["old_quantity"] or 0)
                unit_cost = money(Decimal(str(row["current_sale_price"] or 0)) * Decimal("0.20"))
                metadata = row["metadata"] if isinstance(row["metadata"], dict) else {}
                metadata.update(
                    {
                        "previousQuantityBeforeGroupReduction": old_quantity,
                        "plannedQuantity": quantity,
                        "receivedQuantity": quantity,
                        "quantityRule": "Phụ kiện công nghệ 45; nhóm còn lại 12",
                        "adjustedByMaintenanceScript": True,
                    }
                )

                await conn.execute(
                    """
                    UPDATE inventory_document_lines
                    SET requested_quantity = $2,
                        approved_quantity = $2,
                        expected_quantity = $2,
                        unit_cost = $3,
                        metadata = $4::jsonb
                    WHERE id = $1
                    """,
                    row["line_id"],
                    quantity,
                    unit_cost,
                    json.dumps(metadata, ensure_ascii=False),
                )

                if row["level_id"]:
                    await conn.execute(
                        """
                        UPDATE inventory_levels
                        SET on_hand_quantity = $2,
                            average_unit_cost = $3,
                            updated_at = NOW()
                        WHERE id = $1
                        """,
                        row["level_id"],
                        quantity,
                        unit_cost,
                    )

                if row["lot_id"]:
                    await conn.execute(
                        """
                        UPDATE inventory_lots
                        SET initial_quantity = $2,
                            remaining_quantity = $2,
                            unit_cost = $3,
                            updated_at = NOW(),
                            metadata = metadata || $4::jsonb
                        WHERE id = $1
                        """,
                        row["lot_id"],
                        quantity,
                        unit_cost,
                        json.dumps(
                            {
                                "previousQuantityBeforeGroupReduction": old_quantity,
                                "quantityRule": "Phụ kiện công nghệ 45; nhóm còn lại 12",
                            },
                            ensure_ascii=False,
                        ),
                    )

                await conn.execute(
                    """
                    UPDATE inventory_adjustment_logs
                    SET new_quantity = $2,
                        delta = $2,
                        unit_cost = $3,
                        note = COALESCE(note, '') || $4
                    WHERE reference_code = $1
                      AND variant_id = $5
                      AND transaction_type = 'RECEIPT'
                    """,
                    REFERENCE_CODE,
                    quantity,
                    unit_cost,
                    " | Điều chỉnh số lượng nhập theo nhóm: phụ kiện công nghệ 45, nhóm còn lại 12.",
                    row["variant_id"],
                )

                await conn.execute(
                    """
                    UPDATE product_variants
                    SET stock_quantity = $2,
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    row["variant_id"],
                    quantity,
                )

                affected_product_ids.add(str(row["product_id"]))
                changed_variants.append(
                    {
                        "variantId": str(row["variant_id"]),
                        "oldQuantity": old_quantity,
                        "newQuantity": quantity,
                        "category": row["category_name"],
                    }
                )

            for product_id in affected_product_ids:
                await conn.execute(
                    """
                    UPDATE products p
                    SET stock_quantity = COALESCE((
                            SELECT SUM(stock_quantity)::int
                            FROM product_variants
                            WHERE product_id = p.id
                              AND deleted_at IS NULL
                        ), 0),
                        updated_at = NOW()
                    WHERE p.id = $1
                    """,
                    product_id,
                )

            await conn.execute(
                """
                UPDATE inventory_documents
                SET metadata = COALESCE(metadata, '{}'::jsonb) || $2::jsonb
                WHERE id = $1
                """,
                document["id"],
                json.dumps(
                    {
                        "quantityRule": {
                            "technologyAccessory": ACCESSORY_TARGET_QUANTITY,
                            "default": DEFAULT_TARGET_QUANTITY,
                        },
                        "adjustedByMaintenanceScript": "reduce_receipt_quantities_by_group.py",
                    },
                    ensure_ascii=False,
                ),
            )

            await conn.execute(
                """
                INSERT INTO security_audit_logs (id, event_type, metadata, created_at)
                VALUES ($1, $2, $3::jsonb, NOW())
                """,
                uuid4(),
                "inventory_receipt_quantity_reduced_by_group",
                json.dumps(
                    {
                        "referenceCode": REFERENCE_CODE,
                        "documentId": str(document["id"]),
                        "technologyAccessoryQuantity": ACCESSORY_TARGET_QUANTITY,
                        "defaultQuantity": DEFAULT_TARGET_QUANTITY,
                        "lineCount": len(changed_variants),
                    },
                    ensure_ascii=False,
                ),
            )

        summary = await conn.fetchrow(
            """
            SELECT
                COUNT(*)::int AS line_count,
                SUM(l.requested_quantity)::int AS total_quantity,
                COUNT(*) FILTER (WHERE COALESCE(cat.name, '') = 'Phụ kiện công nghệ')::int AS accessory_lines,
                SUM(l.requested_quantity) FILTER (WHERE COALESCE(cat.name, '') = 'Phụ kiện công nghệ')::int AS accessory_quantity
            FROM inventory_document_lines l
            JOIN inventory_documents d ON d.id = l.document_id
            JOIN products p ON p.id = l.product_id
            LEFT JOIN categories cat ON cat.id = p.category_id
            WHERE d.document_no = $1
            """,
            REFERENCE_CODE,
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "referenceCode": REFERENCE_CODE,
                    "lineCount": summary["line_count"],
                    "totalQuantity": summary["total_quantity"],
                    "accessoryLines": summary["accessory_lines"],
                    "accessoryQuantity": summary["accessory_quantity"],
                    "defaultLines": summary["line_count"] - summary["accessory_lines"],
                    "defaultQuantity": summary["total_quantity"] - summary["accessory_quantity"],
                },
                ensure_ascii=False,
            )
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
