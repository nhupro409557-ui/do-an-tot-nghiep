import unicodedata
from uuid import UUID
from fastapi import HTTPException
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


async def sync_parent_price_if_variants_exist(session: AsyncSession, product_id: UUID) -> None:
    has_variants = await session.scalar(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM product_variants
                WHERE product_id = :product_id
                  AND is_active = TRUE
                  AND deleted_at IS NULL
            )
            """
        ),
        {"product_id": product_id},
    )
    if has_variants:
        await sync_parent_price_from_variants(session, product_id)


def normalized_option_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_product_options(options: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    seen_names: set[str] = set()
    for option in options or []:
        name = str(option.get("name") or "").strip()
        values = [str(value).strip() for value in option.get("values") or [] if str(value).strip()]
        if not name and not values:
            continue
        if not name or not values:
            raise HTTPException(status_code=400, detail="Mỗi thuộc tính sản phẩm phải có tên và ít nhất một giá trị.")
        name_key = name.lower()
        if name_key in seen_names:
            raise HTTPException(status_code=400, detail=f"Thuộc tính '{name}' bị trùng.")
        seen_names.add(name_key)
        deduped_values = list(dict.fromkeys(values))
        normalized.append({"name": name, "values": deduped_values})
    return normalized


def extract_product_metadata(specifications: dict) -> tuple[dict, dict, dict]:
    clean_specs = {}
    seo_metadata = {}
    sales_config = {}
    for k, v in (specifications or {}).items():
        if k.startswith("_seo") or k.lower().startswith("seo"):
            seo_key = k[4:] if k.startswith("_seo") else k
            if seo_key:
                seo_key = seo_key[0].lower() + seo_key[1:]
            seo_metadata[seo_key] = v
        elif k in {"_accessoryOffers", "accessoryOffers"}:
            sales_config["accessoryOffers"] = v
        elif k in {"_attachedServices", "attachedServices"}:
            sales_config["attachedServices"] = v
        elif k in {"_warrantyPolicy", "warrantyPolicy"}:
            sales_config["warrantyPolicy"] = v
        elif k in {"_variantSpecKeys", "variantSpecKeys"}:
            sales_config["variantSpecKeys"] = v
            clean_specs[k] = v
        elif k.startswith("_sales") or k.lower().startswith("sales") or k in {"minimumStock", "blockSaleWhenOutOfStock", "cycleCountDays"}:
            sales_config[k.lstrip("_")] = v
        else:
            clean_specs[k] = v
    return clean_specs, seo_metadata, sales_config


def validate_optimized_media(payload: "ProductPayload") -> None:
    if len(payload.images) > 20:
        raise HTTPException(status_code=400, detail="Không thể tải lên quá 20 ảnh.")
    for img in payload.images:
        if img and not (img.startswith("http") or img.startswith("/images/") or img.startswith("data:")):
            raise HTTPException(status_code=400, detail=f"Định dạng URL ảnh không hợp lệ: {img}")


async def resolve_catalog_labels(session: AsyncSession, payload: "ProductPayload") -> tuple[str, str]:
    category = payload.category or "ACCESSORY"
    brand = payload.brand or "Khac"
    if payload.categoryId:
        category_row = (
            await session.execute(
                text("SELECT name FROM categories WHERE id = :id"),
                {"id": payload.categoryId}
            )
        ).mappings().first()
        if category_row:
            category = category_row["name"]
    if payload.brandId:
        brand_row = (
            await session.execute(
                text("SELECT name FROM brands WHERE id = :id"),
                {"id": payload.brandId}
            )
        ).mappings().first()
        if brand_row:
            brand = brand_row["name"]
    return category, brand
