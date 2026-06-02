from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def persisted_sales_config(sales_config: dict) -> dict:
    normalized_accessory_offers: list[dict] = []
    for item in sales_config.get("accessoryOffers", []) or []:
        if not isinstance(item, dict):
            continue
        product_id = str(item.get("productId") or "").strip()
        discount_type = str(item.get("discountType") or "PERCENT").upper()
        if not product_id or discount_type not in {"FIXED", "PERCENT"}:
            continue
        normalized_accessory_offers.append(
            {
                "productId": product_id,
                "discountType": discount_type,
                "discountValue": max(0, float(item.get("discountValue") or 0)),
                "maxQuantity": max(1, int(item.get("maxQuantity") or 1)),
            }
        )
    normalized_attached_services: list[dict] = []
    for item in sales_config.get("attachedServices", []) or []:
        if not isinstance(item, dict):
            continue
        service_id = str(item.get("serviceId") or "").strip()
        if not service_id:
            continue
        normalized_attached_services.append({"serviceId": service_id})
    return {
        "variantSpecKeys": sales_config.get("variantSpecKeys", []) or [],
        "accessoryOffers": normalized_accessory_offers,
        "warrantyPolicy": sales_config.get("warrantyPolicy", {}) if isinstance(sales_config.get("warrantyPolicy"), dict) else {},
        "attachedServices": normalized_attached_services,
        "minimumStock": max(0, int(sales_config.get("minimumStock") or 0)),
        "blockSaleWhenOutOfStock": bool(sales_config.get("blockSaleWhenOutOfStock", True)),
        "preferredLocationCode": sales_config.get("preferredLocationCode", "") or "",
        "preferredLocationName": sales_config.get("preferredLocationName", "") or "",
        "cycleCountDays": int(sales_config.get("cycleCountDays") or 30),
    }


async def sync_parent_price_from_variants(session: AsyncSession, product_id: UUID) -> None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    MIN(price) FILTER (WHERE stock_quantity > 0) AS min_in_stock_price,
                    MIN(COALESCE(sale_price, price)) FILTER (WHERE stock_quantity > 0) AS min_in_stock_sale_price,
                    MIN(price) AS min_price,
                    MIN(COALESCE(sale_price, price)) AS min_sale_price,
                    COALESCE(SUM(stock_quantity) FILTER (WHERE is_active = TRUE AND deleted_at IS NULL), 0) AS total_stock
                FROM product_variants
                WHERE product_id = :product_id AND is_active = TRUE AND deleted_at IS NULL
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().first()
    if row and (row["min_in_stock_price"] is not None or row["min_price"] is not None):
        price = row["min_in_stock_price"] if row["min_in_stock_price"] is not None else row["min_price"]
        sale_price = row["min_in_stock_sale_price"] if row["min_in_stock_sale_price"] is not None else row["min_sale_price"]
        await session.execute(
            text(
                """
                UPDATE products
                SET price = :price,
                    sale_price = :sale_price,
                    stock_quantity = :stock_quantity,
                    is_price_out_of_stock = :is_price_out_of_stock,
                    updated_at = NOW()
                WHERE id = :product_id
                """
            ),
            {
                "product_id": product_id,
                "price": price,
                "sale_price": sale_price,
                "stock_quantity": int(row["total_stock"] or 0),
                "is_price_out_of_stock": row["min_in_stock_price"] is None,
            },
        )
