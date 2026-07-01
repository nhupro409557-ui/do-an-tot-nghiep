from __future__ import annotations

import asyncio
import json
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
REFERENCE_CODE = "NK20260624-BO-SUNG-TON-MOI"


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def preferred_zone(category: str, subcategory: str) -> str:
    text = f"{category} {subcategory}".lower()
    if "phụ kiện" in text:
        return "Dãy A"
    if "camera" in text or "máy ảnh" in text:
        return "Dãy B"
    return "Dãy C"


async def load_locations(conn: asyncpg.Connection) -> dict[str, list[dict]]:
    rows = await conn.fetch(
        """
        SELECT
            loc.id,
            loc.code,
            loc.name,
            loc.zone,
            COALESCE(SUM(il.on_hand_quantity), 0)::int AS on_hand,
            COUNT(il.id)::int AS level_count
        FROM inventory_locations loc
        LEFT JOIN inventory_levels il ON il.location_id = loc.id
        WHERE loc.status = 'ACTIVE'
          AND loc.purpose = 'STORAGE'
        GROUP BY loc.id
        ORDER BY loc.zone, loc.sort_order, loc.code
        """
    )
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["zone"], []).append(dict(row))
    return grouped


def pick_location(grouped_locations: dict[str, list[dict]], zone: str) -> dict:
    candidates = grouped_locations.get(zone) or grouped_locations.get("Dãy C") or []
    if not candidates:
        raise RuntimeError(f"Không có kệ ACTIVE/STORAGE cho {zone}.")
    selected = min(candidates, key=lambda item: (int(item["on_hand"] or 0), int(item["level_count"] or 0), item["code"]))
    return selected


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
                raise RuntimeError(f"Phiếu {REFERENCE_CODE} đang ở trạng thái {document['status']}, không phải COMPLETED.")

            grouped_locations = await load_locations(conn)
            lines = await conn.fetch(
                """
                SELECT
                    l.id AS line_id,
                    l.metadata,
                    p.id AS product_id,
                    p.name AS product_name,
                    p.sku AS product_sku,
                    COALESCE(cat.name, '') AS category_name,
                    COALESCE(subcat.name, '') AS subcategory_name,
                    pv.id AS variant_id,
                    pv.sku AS variant_sku,
                    COALESCE(NULLIF(pv.stock_quantity, 0), l.requested_quantity, 0)::int AS current_quantity,
                    COALESCE(NULLIF(pv.sale_price, 0), NULLIF(pv.price, 0), NULLIF(p.sale_price, 0), p.price, 0)::numeric AS current_sale_price,
                    il.id AS level_id,
                    il.location_id AS current_level_location_id,
                    il.on_hand_quantity AS level_quantity,
                    il.reserved_quantity AS level_reserved_quantity,
                    lot.id AS lot_id
                FROM inventory_document_lines l
                JOIN products p ON p.id = l.product_id
                LEFT JOIN categories cat ON cat.id = p.category_id
                LEFT JOIN categories subcat ON subcat.id = p.subcategory_id
                LEFT JOIN product_variants pv ON pv.id = l.variant_id
                LEFT JOIN LATERAL (
                    SELECT id, location_id, on_hand_quantity, reserved_quantity
                    FROM inventory_levels
                    WHERE variant_id = l.variant_id
                      AND on_hand_quantity > 0
                    ORDER BY (location_id = (SELECT id FROM inventory_locations WHERE code = 'MAIN')) DESC,
                             on_hand_quantity DESC,
                             updated_at DESC
                    LIMIT 1
                ) il ON TRUE
                LEFT JOIN inventory_lots lot ON lot.source_document_id = l.document_id AND lot.variant_id = l.variant_id
                WHERE l.document_id = $1
                ORDER BY category_name, subcategory_name, p.name, pv.sku
                FOR UPDATE OF l
                """,
                document["id"],
            )
            if not lines:
                raise RuntimeError(f"Phiếu {REFERENCE_CODE} không có dòng sản phẩm.")

            updated = []
            for line in lines:
                quantity = int(line["current_quantity"] or line["level_quantity"] or 0)
                if quantity <= 0:
                    continue
                unit_cost = money(Decimal(str(line["current_sale_price"] or 0)) * Decimal("0.20"))
                zone = preferred_zone(line["category_name"], line["subcategory_name"])
                location = pick_location(grouped_locations, zone)
                target_location_id = location["id"]
                metadata = line["metadata"] if isinstance(line["metadata"], dict) else {}
                metadata.update(
                    {
                        "plannedQuantity": quantity,
                        "receivedQuantity": quantity,
                        "storageLocationCode": location["code"],
                        "storageLocationName": location["name"],
                        "reconcilesExistingStock": True,
                        "stockMutationSkipped": True,
                        "arrangedByMaintenanceScript": True,
                    }
                )

                await conn.execute(
                    """
                    UPDATE inventory_document_lines
                    SET location_id = $2,
                        requested_quantity = $3,
                        approved_quantity = $3,
                        expected_quantity = $3,
                        unit_cost = $4,
                        metadata = $5::jsonb
                    WHERE id = $1
                    """,
                    line["line_id"],
                    target_location_id,
                    quantity,
                    unit_cost,
                    json.dumps(metadata, ensure_ascii=False),
                )

                existing_target_level = await conn.fetchrow(
                    """
                    SELECT id, on_hand_quantity, reserved_quantity, average_unit_cost
                    FROM inventory_levels
                    WHERE variant_id = $1 AND location_id = $2
                    FOR UPDATE
                    """,
                    line["variant_id"],
                    target_location_id,
                )
                if existing_target_level and existing_target_level["id"] != line["level_id"]:
                    old_qty = int(existing_target_level["on_hand_quantity"] or 0)
                    moved_qty = int(line["level_quantity"] or quantity)
                    combined_qty = old_qty + moved_qty
                    old_cost = Decimal(str(existing_target_level["average_unit_cost"] or 0))
                    combined_cost = unit_cost
                    if combined_qty > 0 and old_qty > 0:
                        combined_cost = money(((old_cost * old_qty) + (unit_cost * moved_qty)) / combined_qty)
                    await conn.execute(
                        """
                        UPDATE inventory_levels
                        SET on_hand_quantity = $2,
                            reserved_quantity = reserved_quantity + $3,
                            average_unit_cost = $4,
                            updated_at = NOW()
                        WHERE id = $1
                        """,
                        existing_target_level["id"],
                        combined_qty,
                        int(line["level_reserved_quantity"] or 0),
                        combined_cost,
                    )
                    await conn.execute("DELETE FROM inventory_levels WHERE id = $1", line["level_id"])
                else:
                    await conn.execute(
                        """
                        UPDATE inventory_levels
                        SET location_id = $2,
                            on_hand_quantity = $3,
                            average_unit_cost = $4,
                            updated_at = NOW()
                        WHERE id = $1
                        """,
                        line["level_id"],
                        target_location_id,
                        quantity,
                        unit_cost,
                    )

                await conn.execute(
                    """
                    UPDATE inventory_lots
                    SET location_id = $2,
                        initial_quantity = $3,
                        remaining_quantity = $3,
                        unit_cost = $4,
                        updated_at = NOW(),
                        metadata = metadata || $5::jsonb
                    WHERE id = $1
                    """,
                    line["lot_id"],
                    target_location_id,
                    quantity,
                    unit_cost,
                    json.dumps({"storageLocationCode": location["code"], "storageLocationName": location["name"]}, ensure_ascii=False),
                )

                await conn.execute(
                    """
                    UPDATE inventory_adjustment_logs
                    SET unit_cost = $2,
                        location_code = $3,
                        location_name = $4
                    WHERE reference_code = $1
                      AND variant_id = $5
                      AND transaction_type = 'RECEIPT'
                    """,
                    REFERENCE_CODE,
                    unit_cost,
                    location["code"],
                    location["name"],
                    line["variant_id"],
                )

                location["on_hand"] = int(location["on_hand"] or 0) + quantity
                location["level_count"] = int(location["level_count"] or 0) + 1
                updated.append(
                    {
                        "variantSku": line["variant_sku"],
                        "quantity": quantity,
                        "unitCost": int(unit_cost),
                        "location": location["code"],
                    }
                )

            await conn.execute(
                """
                UPDATE inventory_documents
                SET target_location_id = (
                        SELECT location_id
                        FROM inventory_document_lines
                        WHERE document_id = $1
                        ORDER BY created_at, id
                        LIMIT 1
                    ),
                    metadata = metadata || $2::jsonb
                WHERE id = $1
                """,
                document["id"],
                json.dumps(
                    {
                        "unitCostRule": "20% giá bán hiện hành",
                        "shelfArrangement": "Phụ kiện: Dãy A; Camera/Máy ảnh: Dãy B; còn lại: Dãy C",
                        "arrangedByMaintenanceScript": True,
                    },
                    ensure_ascii=False,
                ),
            )

            await conn.execute(
                """
                INSERT INTO security_audit_logs (user_id, event_type, ip_address, user_agent, metadata)
                VALUES (NULL, 'inventory_receipt_shelf_arranged', 'system', NULL, $1::jsonb)
                """,
                json.dumps(
                    {
                        "referenceCode": REFERENCE_CODE,
                        "lineCount": len(updated),
                        "totalQuantity": sum(item["quantity"] for item in updated),
                        "unitCostRule": "20% giá bán hiện hành",
                    },
                    ensure_ascii=False,
                ),
            )

        summary = await conn.fetchrow(
            """
            SELECT
                COUNT(*)::int AS line_count,
                COALESCE(SUM(requested_quantity), 0)::int AS total_quantity,
                COUNT(*) FILTER (WHERE unit_cost IS NULL OR unit_cost = 0)::int AS missing_cost
            FROM inventory_document_lines l
            JOIN inventory_documents d ON d.id = l.document_id
            WHERE d.document_no = $1
            """,
            REFERENCE_CODE,
        )
        main_qty = await conn.fetchval(
            """
            SELECT COALESCE(SUM(il.on_hand_quantity), 0)::int
            FROM inventory_levels il
            JOIN inventory_locations loc ON loc.id = il.location_id
            WHERE loc.code = 'MAIN'
              AND il.variant_id IN (
                  SELECT variant_id
                  FROM inventory_document_lines l
                  JOIN inventory_documents d ON d.id = l.document_id
                  WHERE d.document_no = $1
              )
            """,
            REFERENCE_CODE,
        )
        by_zone = await conn.fetch(
            """
            SELECT loc.zone, COUNT(*)::int AS level_count, SUM(il.on_hand_quantity)::int AS quantity
            FROM inventory_levels il
            JOIN inventory_locations loc ON loc.id = il.location_id
            WHERE il.variant_id IN (
                SELECT variant_id
                FROM inventory_document_lines l
                JOIN inventory_documents d ON d.id = l.document_id
                WHERE d.document_no = $1
            )
            GROUP BY loc.zone
            ORDER BY loc.zone
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
                    "missingCost": summary["missing_cost"],
                    "mainQuantityAfter": main_qty,
                    "byZone": [dict(row) for row in by_zone],
                },
                ensure_ascii=False,
            )
        )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
