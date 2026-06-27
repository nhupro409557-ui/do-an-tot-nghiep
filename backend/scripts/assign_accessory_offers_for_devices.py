"""Assign sellable accessory offers for phones, laptops and tablets.

The script is idempotent: it appends suitable accessory offers that are not
already configured and keeps existing manual offers intact.
"""

import asyncio
import json
from decimal import Decimal
from uuid import UUID

from sqlalchemy import bindparam, text

from app.infrastructure.database.session import AsyncSessionFactory


TARGET_ROOT_CODES = {"smartphones", "laptops", "tablets"}
MAX_OFFERS_PER_PRODUCT = 4
REBUILD_TARGET_ACCESSORY_OFFERS = True

ACCESSORY_CODES_BY_ROOT = {
    "smartphones": {
        "adapter-gan",
        "adapter-multiport",
        "adapter-wireless",
        "cable-usbc",
        "cable-lightning",
        "audio-tws",
    },
    "tablets": {
        "adapter-gan",
        "adapter-multiport",
        "adapter-wireless",
        "cable-usbc",
        "cable-lightning",
        "audio-tws",
        "cable-thunderbolt",
    },
    "laptops": {
        "adapter-gan",
        "adapter-multiport",
        "cable-usbc",
        "cable-thunderbolt",
        "audio-overear",
        "audio-gaming",
    },
}

LAPTOP_NAME_KEYWORDS = ("chuột", "bàn phím", "keyboard", "mouse")


def current_price(row: dict) -> Decimal:
    sale_price = Decimal(row["sale_price"] or 0)
    if sale_price > 0:
        return sale_price
    return Decimal(row["price"] or 0)


def offer_discount(price: Decimal) -> dict:
    if price < Decimal("2000000"):
        return {"discountType": "PERCENT", "discountValue": 10}
    if price < Decimal("5000000"):
        return {"discountType": "FIXED", "discountValue": 300000}
    return {"discountType": "FIXED", "discountValue": 400000}


def normalized_sales_config(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def accessory_matches(root_code: str, accessory: dict) -> bool:
    subcat_code = accessory.get("subcat_code")
    if subcat_code in ACCESSORY_CODES_BY_ROOT[root_code]:
        return True
    if root_code == "laptops":
        name = str(accessory.get("name") or "").lower()
        return any(keyword in name for keyword in LAPTOP_NAME_KEYWORDS)
    return False


def accessory_score(root_code: str, accessory: dict) -> tuple:
    subcat_code = accessory.get("subcat_code") or ""
    price = current_price(accessory)
    stock = int(accessory.get("stock_quantity") or 0)
    preferred_order = {
        "smartphones": ["adapter-gan", "cable-usbc", "cable-lightning", "adapter-wireless", "audio-tws", "adapter-multiport"],
        "tablets": ["adapter-gan", "cable-usbc", "adapter-multiport", "cable-thunderbolt", "adapter-wireless", "audio-tws"],
        "laptops": ["adapter-gan", "adapter-multiport", "cable-thunderbolt", "cable-usbc", "audio-overear", "audio-gaming"],
    }[root_code]
    try:
        order = preferred_order.index(subcat_code)
    except ValueError:
        order = len(preferred_order)
    return (order, -stock, price)


def select_accessories(root_code: str, candidates: list[dict]) -> list[dict]:
    low = [item for item in candidates if current_price(item) < Decimal("2000000")]
    medium = [item for item in candidates if Decimal("2000000") <= current_price(item) < Decimal("5000000")]
    high = [item for item in candidates if current_price(item) >= Decimal("5000000")]
    low.sort(key=lambda item: accessory_score(root_code, item))
    medium.sort(key=lambda item: accessory_score(root_code, item))
    high.sort(key=lambda item: accessory_score(root_code, item))

    buckets = [low, low, medium, high] if root_code in {"smartphones", "tablets"} else [low, medium, medium, high]
    selected: list[dict] = []
    selected_ids = set()
    for bucket in buckets:
        next_item = next((item for item in bucket if item["id"] not in selected_ids), None)
        if next_item:
            selected.append(next_item)
            selected_ids.add(next_item["id"])

    if len(selected) < MAX_OFFERS_PER_PRODUCT:
        fallback = sorted(candidates, key=lambda item: accessory_score(root_code, item))
        for item in fallback:
            if item["id"] in selected_ids:
                continue
            selected.append(item)
            selected_ids.add(item["id"])
            if len(selected) >= MAX_OFFERS_PER_PRODUCT:
                break

    return selected[:MAX_OFFERS_PER_PRODUCT]


async def main() -> None:
    async with AsyncSessionFactory() as session:
        accessory_rows = [
            dict(row)
            for row in (
                await session.execute(
                    text(
                        """
                        SELECT
                            p.id,
                            p.name,
                            p.price,
                            p.sale_price,
                            sc.code AS subcat_code,
                            GREATEST(COALESCE(vs.variant_stock, 0), COALESCE(p.stock_quantity, 0))::int AS stock_quantity
                        FROM products p
                        LEFT JOIN categories c ON c.id = p.category_id
                        LEFT JOIN categories sc ON sc.id = p.subcategory_id
                        LEFT JOIN (
                            SELECT product_id, SUM(stock_quantity) AS variant_stock
                            FROM product_variants
                            WHERE is_active = TRUE
                              AND deleted_at IS NULL
                              AND status NOT IN ('deleted', 'archived', 'inactive', 'discontinued')
                            GROUP BY product_id
                        ) vs ON vs.product_id = p.id
                        WHERE p.status = 'ACTIVE'
                          AND p.deleted_at IS NULL
                          AND c.code = 'accessories'
                          AND GREATEST(COALESCE(vs.variant_stock, 0), COALESCE(p.stock_quantity, 0)) > 0
                        """
                    )
                )
            ).mappings().all()
        ]
        target_rows = [
            dict(row)
            for row in (
                await session.execute(
                    text(
                        """
                        SELECT
                            p.id,
                            p.name,
                            p.sales_config,
                            COALESCE(root.code, c.code, sc.code) AS root_code
                        FROM products p
                        LEFT JOIN categories c ON c.id = p.category_id
                        LEFT JOIN categories sc ON sc.id = p.subcategory_id
                        LEFT JOIN categories root ON root.id = COALESCE(c.parent_id, sc.parent_id)
                        WHERE p.status = 'ACTIVE'
                          AND p.deleted_at IS NULL
                          AND COALESCE(root.code, c.code, sc.code) IN :target_codes
                        """
                    ).bindparams(bindparam("target_codes", expanding=True)),
                    {"target_codes": sorted(TARGET_ROOT_CODES)},
                )
            ).mappings().all()
        ]

        updated = 0
        inserted_relations = 0
        for product in target_rows:
            root_code = str(product["root_code"])
            sales_config = normalized_sales_config(product.get("sales_config"))
            existing_offers = [
                item for item in sales_config.get("accessoryOffers", []) or []
                if isinstance(item, dict) and item.get("productId")
            ]
            accessory_row_ids = {str(item["id"]) for item in accessory_rows}
            preserved_offers = [
                item for item in existing_offers
                if str(item["productId"]) not in accessory_row_ids
            ] if REBUILD_TARGET_ACCESSORY_OFFERS else existing_offers
            existing_ids = {str(item["productId"]) for item in preserved_offers}
            slots = max(0, MAX_OFFERS_PER_PRODUCT - len(preserved_offers))

            candidates = [
                item for item in accessory_rows
                if str(item["id"]) not in existing_ids
                and item["id"] != product["id"]
                and accessory_matches(root_code, item)
            ]
            new_offers = []
            for accessory in select_accessories(root_code, candidates)[:slots]:
                discount = offer_discount(current_price(accessory))
                new_offers.append(
                    {
                        "productId": str(accessory["id"]),
                        "discountType": discount["discountType"],
                        "discountValue": discount["discountValue"],
                        "maxQuantity": 1,
                    }
                )

            if not new_offers:
                continue

            merged_offers = preserved_offers + new_offers
            sales_config["accessoryOffers"] = merged_offers
            await session.execute(
                text(
                    """
                    UPDATE products
                    SET sales_config = CAST(:sales_config AS jsonb),
                        updated_at = NOW()
                    WHERE id = :product_id
                    """
                ),
                {
                    "product_id": product["id"],
                    "sales_config": json.dumps(sales_config, ensure_ascii=False),
                },
            )
            if REBUILD_TARGET_ACCESSORY_OFFERS:
                await session.execute(
                    text("DELETE FROM product_accessories WHERE product_id = :product_id"),
                    {"product_id": product["id"]},
                )
            for offer in merged_offers:
                result = await session.execute(
                    text(
                        """
                        INSERT INTO product_accessories (product_id, accessory_product_id)
                        VALUES (:product_id, :accessory_id)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "product_id": product["id"],
                        "accessory_id": UUID(offer["productId"]),
                    },
                )
                inserted_relations += int(result.rowcount or 0)
            updated += 1

        await session.commit()
        print(f"Updated {updated} products; inserted {inserted_relations} accessory relations.")


if __name__ == "__main__":
    asyncio.run(main())
