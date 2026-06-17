import unicodedata
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import product_repo


PRODUCT_PUBLICATION_STATUSES = {"ACTIVE", "INACTIVE", "DISCONTINUED"}


def normalize_target_product_status(value: object) -> str:
    status = str(value or "ACTIVE").upper()
    return status if status in PRODUCT_PUBLICATION_STATUSES else "ACTIVE"


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
    raw_imei_policy = sales_config.get("imeiPolicy") if isinstance(sales_config.get("imeiPolicy"), dict) else {}
    imei_mode = str(raw_imei_policy.get("mode") or "CATEGORY").upper()
    if imei_mode not in {"CATEGORY", "MANUAL"}:
        imei_mode = "CATEGORY"
    raw_serial_policy = sales_config.get("serialPolicy") if isinstance(sales_config.get("serialPolicy"), dict) else {}
    serial_mode = str(raw_serial_policy.get("mode") or "CATEGORY").upper()
    if serial_mode not in {"CATEGORY", "MANUAL"}:
        serial_mode = "CATEGORY"
    return {
        "variantSpecKeys": sales_config.get("variantSpecKeys", []) or [],
        "targetProductStatus": normalize_target_product_status(sales_config.get("targetProductStatus")),
        "accessoryOffers": normalized_accessory_offers,
        "warrantyPolicy": sales_config.get("warrantyPolicy", {}) if isinstance(sales_config.get("warrantyPolicy"), dict) else {},
        "attachedServices": normalized_attached_services,
        "imeiPolicy": {
            "mode": imei_mode,
            "trackImei": bool(raw_imei_policy.get("trackImei", False)),
        },
        "serialPolicy": {
            "mode": serial_mode,
            "trackSerialNumber": bool(raw_serial_policy.get("trackSerialNumber", False)),
        },
        "minimumStock": max(0, int(sales_config.get("minimumStock") or 0)),
        "blockSaleWhenOutOfStock": bool(sales_config.get("blockSaleWhenOutOfStock", True)),
        "cycleCountDays": int(sales_config.get("cycleCountDays") or 30),
    }


async def sync_parent_price_from_variants(session: AsyncSession, product_id: UUID) -> None:
    row = await product_repo.get_variant_price_summary(session, product_id)
    if row and (row["min_in_stock_price"] is not None or row["min_price"] is not None):
        price = row["min_in_stock_price"] if row["min_in_stock_price"] is not None else row["min_price"]
        sale_price = row["min_in_stock_sale_price"] if row["min_in_stock_sale_price"] is not None else row["min_sale_price"]
        await product_repo.update_parent_price_from_summary(
            session,
            product_id=product_id,
            price=price,
            sale_price=sale_price,
            stock_quantity=int(row["total_stock"] or 0),
            is_price_out_of_stock=row["min_in_stock_price"] is None,
        )


async def sync_parent_price_if_variants_exist(session: AsyncSession, product_id: UUID) -> None:
    if await product_repo.has_active_variants(session, product_id):
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
    for key, value in (specifications or {}).items():
        if key.startswith("_seo") or key.lower().startswith("seo"):
            seo_key = key[4:] if key.startswith("_seo") else key
            if seo_key:
                seo_key = seo_key[0].lower() + seo_key[1:]
            seo_metadata[seo_key] = value
        elif key in {"_accessoryOffers", "accessoryOffers"}:
            sales_config["accessoryOffers"] = value
        elif key in {"_attachedServices", "attachedServices"}:
            sales_config["attachedServices"] = value
        elif key in {"_warrantyPolicy", "warrantyPolicy"}:
            sales_config["warrantyPolicy"] = value
        elif key in {"_imeiPolicy", "imeiPolicy"}:
            sales_config["imeiPolicy"] = value
        elif key in {"_serialPolicy", "serialPolicy"}:
            sales_config["serialPolicy"] = value
        elif key in {"_targetProductStatus", "targetProductStatus"}:
            sales_config["targetProductStatus"] = value
        elif key in {"_variantSpecKeys", "variantSpecKeys"}:
            sales_config["variantSpecKeys"] = value
            clean_specs[key] = value
        elif key.startswith("_sales") or key.lower().startswith("sales") or key in {"minimumStock", "blockSaleWhenOutOfStock", "cycleCountDays"}:
            sales_config[key.lstrip("_")] = value
        else:
            clean_specs[key] = value
    return clean_specs, seo_metadata, sales_config


def validate_optimized_media(payload: object) -> None:
    images = getattr(payload, "images", [])
    if len(images) > 20:
        raise HTTPException(status_code=400, detail="Không thể tải lên quá 20 ảnh.")
    for image in images:
        if image and not (image.startswith("http") or image.startswith("/images/") or image.startswith("data:")):
            raise HTTPException(status_code=400, detail=f"Định dạng URL ảnh không hợp lệ: {image}")


async def resolve_catalog_labels(session: AsyncSession, payload: object) -> tuple[str, str]:
    category = getattr(payload, "category", None) or "ACCESSORY"
    brand = getattr(payload, "brand", None) or "Khac"
    category_id = getattr(payload, "categoryId", None)
    brand_id = getattr(payload, "brandId", None)
    if category_id:
        category_name = await product_repo.get_category_name(session, category_id)
        if category_name:
            category = category_name
    if brand_id:
        brand_name = await product_repo.get_brand_name(session, brand_id)
        if brand_name:
            brand = brand_name
    return category, brand
