import argparse
import asyncio
import json
import os
import re
import unicodedata
from collections import defaultdict
from typing import Any

import asyncpg


DEFAULT_DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"

META_SPEC_KEYS = {
    "_variantSpecKeys",
    "_seoTitle",
    "_seoDescription",
    "_seoSlug",
    "_accessoryProducts",
    "_accessoryOffers",
    "_attachedServices",
    "_warrantyPolicy",
    "_imeiPolicy",
    "_serialPolicy",
    "_targetProductStatus",
}

PRODUCT_SPEC_OVERRIDES = {
    "SAM-ZFLIP5": {
        "ram": "8GB",
    },
    "VIV-V30PRO": {
        "ram": "12GB",
        "storage": "512GB",
    },
    "XIM-RN13P5G": {
        "ram": "8GB",
        "storage": "256GB",
    },
}

STATIC_KEY_ALIASES = {
    "screenSize": "screen_size",
    "displayType": "display_type",
    "displayFeatures": "display_features",
    "rearVideo": "rear_video",
    "frontVideo": "front_video",
    "rearCameraFeatures": "rear_camera_features",
    "frontCameraFeatures": "front_camera_features",
    "chargingPort": "charging_port",
    "waterResistance": "water_resistance",
    "frameMaterial": "frame_material",
    "backMaterial": "back_material",
    "releaseTime": "release_time",
    "specialFeatures": "special_features",
    "memoryCard": "memory_card",
    "caseSize": "case_size",
    "sportsModes": "sports_modes",
    "fieldOfView": "field_of_view",
}

SPEC_KEY_ALIASES = {
    "processor": ["chip xu ly", "bo xu ly", "cpu"],
    "storage": ["storage", "rom", "bo nho trong", "bo nho", "o cung", "dung luong"],
    "ram": ["ram", "bo nho ram"],
    "battery": ["battery", "pin", "dung luong pin", "thoi luong pin"],
    "charging": ["charging", "sac", "sac nhanh", "cong nghe sac"],
    "connectivity": ["connectivity", "ket noi", "chuan ket noi", "ket noi khong day"],
    "water_resistance": ["water resistance", "chong nuoc", "khang nuoc", "chuan chong nuoc"],
    "weight": ["weight", "trong luong"],
    "dimensions": ["dimensions", "kich thuoc"],
    "material": ["material", "chat lieu", "chat lieu vo", "chat lieu khung"],
    "ports": ["ports", "cong ket noi", "so cong", "so cong ket noi", "cong ra"],
    "power": ["power", "cong suat", "cong suat toi da", "tong cong suat", "cong suat ho tro", "cong suat sac", "cong suat ra"],
    "capacity": ["capacity", "dung luong"],
    "charging_standard": ["charging standard", "chuan sac", "ho tro chuan sac"],
    "screen_size": ["screen size", "screen_size", "man hinh", "man hinh trong", "kich thuoc man", "kich thuoc man hinh"],
    "screen_technology": ["screen technology", "cong nghe man hinh"],
    "resolution": ["resolution", "do phan giai", "do phan giai video"],
    "refresh_rate": ["refresh rate", "tan so quet"],
    "brightness": ["brightness", "do sang", "do sang toi da"],
    "rear_camera": ["rear camera", "camera sau", "camera chinh", "camera truoc/sau"],
    "front_camera": ["front camera", "camera truoc"],
    "video_recording": ["video recording", "quay video", "quay phim"],
    "sensor": ["sensor", "cam bien", "kich thuoc cam bien"],
    "lens": ["lens", "ong kinh"],
    "zoom": ["zoom"],
    "field_of_view": ["field of view", "goc nhin", "goc nhin ong kinh", "goc xoay ngang"],
    "case_size": ["case size", "kich thuoc mat"],
    "strap": ["strap", "day deo"],
    "sports_modes": ["sports modes", "che do luyen tap", "so che do the thao"],
    "color": ["color", "mau", "mau sac"],
    "configuration": ["configuration", "cau hinh", "phien ban"],
}


def asyncpg_dsn(value: str) -> str:
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


def as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def as_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return list(parsed) if isinstance(parsed, list) else []
    return []


def clean(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return str(value).strip()


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFD", clean(value))
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def json_changed(before: Any, after: Any) -> bool:
    return json.dumps(before, ensure_ascii=False, sort_keys=True) != json.dumps(after, ensure_ascii=False, sort_keys=True)


def parse_options(field: dict) -> list[str]:
    return [item.strip() for item in clean(field.get("options")).split(",") if item.strip()]


def normalize_option_value(value: Any, field: dict) -> Any:
    text = clean(value)
    if not text:
        return value
    options = parse_options(field)
    if not options:
        return value
    unit = clean(field.get("unit"))
    normalized_text = normalize_text(text).replace(" ", "")
    for option in options:
        if text == option:
            return option
        normalized_option = normalize_text(option).replace(" ", "")
        if normalized_text == normalized_option:
            return option
        if unit:
            normalized_unit = normalize_text(unit).replace(" ", "")
            if normalized_text == f"{normalized_option}{normalized_unit}":
                return option
            suffix = normalize_text(unit).strip()
            stripped = re.sub(rf"\s*{re.escape(suffix)}$", "", normalize_text(text)).strip()
            if stripped.replace(" ", "") == normalized_option:
                return option
    return value


def build_field_lookup(spec_fields: list[dict]) -> tuple[dict[str, dict], dict[str, str]]:
    fields_by_key: dict[str, dict] = {}
    lookup: dict[str, str] = {}
    for field in spec_fields:
        key = clean(field.get("key"))
        if not key or key in fields_by_key:
            continue
        fields_by_key[key] = field
        lookup[normalize_text(key)] = key
        lookup[normalize_text(field.get("label") or key)] = key

    for alias, canonical in STATIC_KEY_ALIASES.items():
        if canonical in fields_by_key:
            lookup[normalize_text(alias)] = canonical

    for canonical, aliases in SPEC_KEY_ALIASES.items():
        if canonical not in fields_by_key:
            continue
        for alias in aliases:
            normalized_alias = normalize_text(alias)
            if normalized_alias not in lookup:
                lookup[normalized_alias] = canonical

    if "capacity" in fields_by_key:
        lookup[normalize_text("dung luong")] = "capacity"
    elif "storage" in fields_by_key:
        lookup[normalize_text("dung luong")] = "storage"
    if "battery" in fields_by_key:
        lookup[normalize_text("dung luong pin")] = "battery"
        lookup[normalize_text("pin")] = "battery"

    return fields_by_key, lookup


def canonical_key(key: str, lookup: dict[str, str], fields_by_key: dict[str, dict]) -> str:
    if key in META_SPEC_KEYS:
        return key
    if key in fields_by_key:
        return key
    if key in STATIC_KEY_ALIASES and STATIC_KEY_ALIASES[key] in fields_by_key:
        return STATIC_KEY_ALIASES[key]
    return lookup.get(normalize_text(key), key)


def canonicalize_mapping(data: dict, fields_by_key: dict[str, dict], lookup: dict[str, str]) -> dict:
    result: dict[str, Any] = {}
    for key, value in data.items():
        target_key = canonical_key(str(key), lookup, fields_by_key)
        field = fields_by_key.get(target_key)
        normalized_value = normalize_option_value(value, field) if field else value
        if target_key in result and clean(result[target_key]):
            continue
        result[target_key] = normalized_value
    return result


def variant_source_value(variant: dict, key: str, field: dict, lookup: dict[str, str]) -> str:
    if key == "ram":
        return clean(variant.get("ram"))
    if key == "storage":
        return clean(variant.get("storage"))
    if key == "configuration":
        return clean(variant.get("configuration"))
    if key == "color":
        return clean(variant.get("color_name"))

    label = field.get("label") or key
    specs = as_dict(variant.get("specs"))
    attrs = as_dict(variant.get("attributes"))
    for source in (specs, attrs):
        for raw_key, value in source.items():
            if canonical_key(str(raw_key), lookup, {key: field}) == key or normalize_text(raw_key) == normalize_text(label):
                return clean(value)
    return ""


def normalize_product_specs(product: dict, variants: list[dict], spec_fields: list[dict]) -> tuple[dict, list[str]]:
    fields_by_key, lookup = build_field_lookup(spec_fields)
    specs = canonicalize_mapping(as_dict(product.get("specifications")), fields_by_key, lookup)
    for key, value in PRODUCT_SPEC_OVERRIDES.get(clean(product.get("sku")), {}).items():
        if key in fields_by_key and not clean(specs.get(key)):
            specs[key] = value
    variant_keys = [
        clean(field.get("key"))
        for field in spec_fields
        if field.get("variant") and clean(field.get("key"))
    ]

    existing_variant_keys = [
        canonical_key(str(key), lookup, fields_by_key)
        for key in as_list(specs.get("_variantSpecKeys"))
        if clean(key)
    ]
    final_variant_keys: list[str] = []
    for key in [*existing_variant_keys, *variant_keys]:
        if key not in variant_keys or key in final_variant_keys:
            continue
        field = fields_by_key[key]
        if any(variant_source_value(variant, key, field, lookup) for variant in variants):
            final_variant_keys.append(key)
    if final_variant_keys:
        specs["_variantSpecKeys"] = final_variant_keys
    elif "_variantSpecKeys" in specs:
        specs["_variantSpecKeys"] = []

    issues: list[str] = []
    active_variants = [
        variant
        for variant in variants
        if variant.get("is_active") is not False
        and clean(variant.get("status")).lower() not in {"deleted", "archived", "inactive", "discontinued"}
    ]
    for field in spec_fields:
        key = clean(field.get("key"))
        if not key or not field.get("required"):
            continue
        if key in final_variant_keys and active_variants:
            missing_skus = [
                clean(variant.get("sku")) or str(variant.get("id"))
                for variant in active_variants
                if not variant_source_value(variant, key, field, lookup)
            ]
            if missing_skus:
                issues.append(f"Thiếu thông số biến thể {key}: {', '.join(missing_skus[:5])}")
        elif not clean(specs.get(key)):
            issues.append(f"Thiếu thông số sản phẩm bắt buộc {key}")
    return specs, issues


def normalize_variant(variant: dict, spec_fields: list[dict]) -> dict:
    fields_by_key, lookup = build_field_lookup(spec_fields)
    specs = canonicalize_mapping(as_dict(variant.get("specs")), fields_by_key, lookup)
    attrs = canonicalize_mapping(as_dict(variant.get("attributes")), fields_by_key, lookup)
    next_attrs = as_dict(variant.get("attributes"))

    for field in spec_fields:
        key = clean(field.get("key"))
        if not key or not field.get("variant"):
            continue
        value = clean(specs.get(key)) or variant_source_value(variant, key, field, lookup)
        if not value:
            continue
        value = normalize_option_value(value, field)
        specs[key] = value
        label = clean(field.get("label")) or key
        if label and not clean(next_attrs.get(label)):
            next_attrs[label] = value
        if key in attrs and not clean(next_attrs.get(key)):
            next_attrs[key] = attrs[key]

    return {
        "specs": specs,
        "attributes": next_attrs,
    }


async def fetch_spec_fields(conn: asyncpg.Connection, category_id: str | None) -> list[dict]:
    if not category_id:
        return []
    rows = await conn.fetch(
        """
        WITH RECURSIVE ancestors AS (
            SELECT id, parent_id, spec_fields, 0 AS depth
            FROM categories
            WHERE id = $1 AND COALESCE(is_deleted, FALSE) = FALSE
            UNION ALL
            SELECT c.id, c.parent_id, c.spec_fields, ancestors.depth + 1
            FROM categories c
            JOIN ancestors ON ancestors.parent_id = c.id
            WHERE COALESCE(c.is_deleted, FALSE) = FALSE
        )
        SELECT spec_fields
        FROM ancestors
        ORDER BY depth DESC
        """,
        category_id,
    )
    spec_fields: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        for field in as_list(row["spec_fields"]):
            if not isinstance(field, dict):
                continue
            key = clean(field.get("key"))
            if not key or key in seen:
                continue
            seen.add(key)
            spec_fields.append(field)
    return spec_fields


async def run(args: argparse.Namespace) -> None:
    conn = await asyncpg.connect(asyncpg_dsn(args.database_url))
    try:
        where = ["p.deleted_at IS NULL", "p.parent_product_id IS NULL"]
        params: list[Any] = []
        if args.sku:
            params.append(args.sku)
            where.append(f"p.sku = ${len(params)}")
        if not args.include_inactive:
            where.append("p.status IN ('ACTIVE', 'DRAFT', 'PENDING', 'APPROVED')")

        products = await conn.fetch(
            f"""
            SELECT
                p.id, p.sku, p.name, p.category_id, p.subcategory_id,
                p.specifications
            FROM products p
            WHERE {' AND '.join(where)}
            ORDER BY p.name
            """,
            *params,
        )
        product_ids = [row["id"] for row in products]
        variant_rows = await conn.fetch(
            """
            SELECT id, product_id, sku, color_name, storage, ram, configuration,
                   specs, attributes, is_active, status
            FROM product_variants
            WHERE deleted_at IS NULL
              AND product_id = ANY($1::uuid[])
            ORDER BY product_id, sku
            """,
            product_ids,
        ) if product_ids else []
        variants_by_product: dict[str, list[dict]] = defaultdict(list)
        for row in variant_rows:
            variants_by_product[str(row["product_id"])].append(dict(row))

        product_updates: list[tuple[asyncpg.Record, dict, list[str]]] = []
        variant_updates: list[tuple[dict, dict]] = []
        product_issues: list[tuple[str, str, list[str]]] = []

        spec_cache: dict[str, list[dict]] = {}
        for product in products:
            leaf_id = product["subcategory_id"] or product["category_id"]
            leaf_key = str(leaf_id) if leaf_id else ""
            if leaf_key not in spec_cache:
                spec_cache[leaf_key] = await fetch_spec_fields(conn, leaf_id)
            spec_fields = spec_cache[leaf_key]
            if not spec_fields:
                continue

            variants = variants_by_product.get(str(product["id"]), [])
            next_specs, issues = normalize_product_specs(dict(product), variants, spec_fields)
            if issues:
                product_issues.append((product["sku"], product["name"], issues))
            if json_changed(as_dict(product["specifications"]), next_specs):
                product_updates.append((product, next_specs, issues))

            for variant in variants:
                normalized = normalize_variant(variant, spec_fields)
                if json_changed(as_dict(variant.get("specs")), normalized["specs"]) or json_changed(as_dict(variant.get("attributes")), normalized["attributes"]):
                    variant_updates.append((variant, normalized))

        print(f"Sản phẩm quét: {len(products)}")
        print(f"Sản phẩm cần cập nhật specifications: {len(product_updates)}")
        print(f"Biến thể cần cập nhật specs/attributes: {len(variant_updates)}")
        print(f"Sản phẩm còn cảnh báo bắt buộc: {len(product_issues)}")
        for product, next_specs, issues in product_updates[: args.preview_limit]:
            before_keys = set(as_dict(product["specifications"]).keys())
            after_keys = set(next_specs.keys())
            added = sorted(after_keys - before_keys)
            removed = sorted(before_keys - after_keys)
            print(f"- {product['sku']} | {product['name']}: +{added} -{removed}")
            for issue in issues:
                print(f"  Cảnh báo: {issue}")
        for sku, name, issues in product_issues[: args.preview_limit]:
            if any(product["sku"] == sku for product, _, _ in product_updates[: args.preview_limit]):
                continue
            print(f"- {sku} | {name}")
            for issue in issues:
                print(f"  Cảnh báo: {issue}")

        if not args.apply:
            print("Dry-run: chưa ghi dữ liệu. Chạy lại với --apply để cập nhật database.")
            return

        async with conn.transaction():
            for product, next_specs, _ in product_updates:
                await conn.execute(
                    """
                    UPDATE products
                    SET specifications = $1::jsonb,
                        updated_at = NOW()
                    WHERE id = $2
                    """,
                    json.dumps(next_specs, ensure_ascii=False),
                    product["id"],
                )
            for variant, normalized in variant_updates:
                await conn.execute(
                    """
                    UPDATE product_variants
                    SET specs = $1::jsonb,
                        attributes = $2::jsonb
                    WHERE id = $3
                    """,
                    json.dumps(normalized["specs"], ensure_ascii=False),
                    json.dumps(normalized["attributes"], ensure_ascii=False),
                    variant["id"],
                )
        print("Đã cập nhật dữ liệu sản phẩm theo thông số danh mục.")
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Chuẩn hóa thông số sản phẩm theo spec_fields của danh mục.")
    parser.add_argument("--apply", action="store_true", help="Ghi thay đổi vào database. Mặc định chỉ dry-run.")
    parser.add_argument("--include-inactive", action="store_true", help="Quét cả sản phẩm đang ẩn/lưu trữ.")
    parser.add_argument("--sku", help="Chỉ chuẩn hóa một SKU cụ thể.")
    parser.add_argument("--preview-limit", type=int, default=30, help="Số dòng preview tối đa.")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        help="DATABASE_URL dạng postgresql:// hoặc postgresql+asyncpg://.",
    )
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
