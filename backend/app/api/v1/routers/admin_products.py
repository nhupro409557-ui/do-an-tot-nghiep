import csv
import io
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id, require_permission, get_current_role_code
from app.api.v1.routers.admin_categories import audit_product_event, ensure_categories_not_migrating
from app.api.v1.routers.admin_product_utils import persisted_sales_config, sync_parent_price_from_variants
from app.api.v1.routers.admin_schemas import *
from app.api.v1.routers.admin_utils import (
    display_status,
    ensure_not_data_url,
    generate_variant_sku,
    normalize_status,
    slugify,
    split_relation_tokens,
    stock_state,
)
from app.infrastructure.database.session import AsyncSessionFactory, get_session


router = APIRouter()
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
MAX_PRODUCT_IMAGE_BYTES = 10 * 1024 * 1024


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
        elif k.startswith("_sales") or k.lower().startswith("sales") or k in {"accessoryOffers", "attachedServices", "warrantyPolicy", "minimumStock", "blockSaleWhenOutOfStock", "preferredLocationCode", "preferredLocationName", "cycleCountDays"}:
            sales_config[k] = v
        else:
            clean_specs[k] = v
    return clean_specs, seo_metadata, sales_config


def validate_optimized_media(payload: "ProductPayload") -> None:
    if len(payload.images) > 20:
        raise HTTPException(status_code=400, detail="Không thể tải lên quá 20 ảnh.")
    for img in payload.images:
        if img and not (img.startswith("http") or img.startswith("/images/") or img.startswith("data:")):
            raise HTTPException(status_code=400, detail=f"Định dạng URL ảnh không hợp lệ: {img}")


async def resolve_product_refs(session: AsyncSession, product_id: UUID) -> None:
    pass


async def sync_product_relations(session: AsyncSession, product_id: UUID, sales_config: dict) -> None:
    # Sync accessories
    await session.execute(
        text("DELETE FROM product_accessories WHERE product_id = :product_id"),
        {"product_id": product_id}
    )
    for offer in sales_config.get("accessoryOffers", []) or []:
        if not isinstance(offer, dict):
            continue
        try:
            acc_id = UUID(str(offer.get("productId") or ""))
        except ValueError:
            continue
        await session.execute(
            text(
                """
                INSERT INTO product_accessories (product_id, accessory_product_id)
                VALUES (:product_id, :accessory_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"product_id": product_id, "accessory_id": acc_id}
        )

    # Sync attached services
    await session.execute(
        text("DELETE FROM product_attached_services WHERE product_id = :product_id"),
        {"product_id": product_id}
    )
    used_service_groups = set()
    for item in sales_config.get("attachedServices", []) or []:
        if not isinstance(item, dict):
            continue
        try:
            service_id = UUID(str(item.get("serviceId") or ""))
        except ValueError:
            continue
        service_row = (
            await session.execute(
                text("SELECT service_type, attribute_group FROM attached_services WHERE id = :id AND is_active = TRUE"),
                {"id": service_id},
            )
        ).mappings().first()
        if not service_row:
            continue
        group_key = f"{service_row['service_type']}:{service_row['attribute_group'] or service_id}"
        if service_row["attribute_group"] and group_key in used_service_groups:
            continue
        used_service_groups.add(group_key)
        await session.execute(
            text(
                """
                INSERT INTO product_attached_services (product_id, service_id, override_price)
                VALUES (:product_id, :service_id, :override_price)
                ON CONFLICT (product_id, service_id)
                DO UPDATE SET override_price = EXCLUDED.override_price
                """
            ),
            {
                "product_id": product_id,
                "service_id": service_id,
                "override_price": None,
            },
        )


@router.get("/products", dependencies=[Depends(require_permission("product:read"))])
async def list_admin_products(
    page: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    cursor: str | None = Query(default=None, max_length=80),
    search: str = Query(default="", max_length=120),
    status_filter: str | None = Query(default=None, alias="status"),
    categoryId: UUID | None = None,
    brandId: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict] | dict:
    search_text = search.strip()
    params = {
        "search": search_text,
        "pattern": f"%{search_text}%",
        "status_filter": status_filter,
        "category_id": categoryId,
        "brand_id": brandId,
    }
    where_sql = """
            WHERE p.deleted_at IS NULL
              AND (p.status NOT IN ('ARCHIVED', 'MERGED') OR CAST(:status_filter AS TEXT) IN ('ARCHIVED', 'MERGED'))
              AND (
                :search = ''
                OR p.name ILIKE :pattern
                OR COALESCE(p.sku, '') ILIKE :pattern
                OR COALESCE(p.brand, '') ILIKE :pattern
                OR COALESCE(p.category, '') ILIKE :pattern
                OR COALESCE(c.name, '') ILIKE :pattern
                OR COALESCE(sc.name, '') ILIKE :pattern
              )
              AND (CAST(:status_filter AS TEXT) IS NULL OR p.status = CAST(:status_filter AS TEXT))
              AND (CAST(:category_id AS UUID) IS NULL OR p.category_id = CAST(:category_id AS UUID) OR p.subcategory_id = CAST(:category_id AS UUID))
              AND (CAST(:brand_id AS UUID) IS NULL OR p.brand_id = CAST(:brand_id AS UUID))
            """
    pagination_sql = ""
    if cursor:
        where_sql += "\n              AND p.id::text < :cursor"
        pagination_sql = "LIMIT :limit"
        params.update({"cursor": cursor, "limit": limit})
    elif page is not None:
        pagination_sql = "LIMIT :limit OFFSET :offset"
        params.update({"limit": limit, "offset": (page - 1) * limit})

    total = None
    if page is not None:
        total_result = await session.execute(
            text(
                f"""
                SELECT COUNT(*) AS total
                FROM products p
                LEFT JOIN categories c ON c.id = p.category_id
                LEFT JOIN categories sc ON sc.id = p.subcategory_id
                {where_sql}
                """
            ),
            params,
        )
        total = int(total_result.scalar() or 0)

    result = await session.execute(
        text(
            f"""
            SELECT
                p.id::text,
                p.sku,
                p.name,
                p.slug,
                p.category,
                p.brand,
                p.category_id::text AS "categoryId",
                p.subcategory_id::text AS "subcategoryId",
                p.brand_id::text AS "brandId",
                c.name AS "categoryName",
                sc.name AS "subcategoryName",
                p.description,
                p.specifications,
                p.price,
                p.sale_price AS "discountPrice",
                p.stock_quantity AS stock,
                p.stock_quantity AS "stockQuantity",
                CASE WHEN p.stock_quantity > 0 THEN 'IN_STOCK' ELSE 'OUT_OF_STOCK' END AS "stockState",
                CASE
                    WHEN p.status = 'ACTIVE' AND p.stock_quantity <= 0 THEN 'Hết hàng'
                    WHEN p.status = 'DRAFT' THEN 'Nháp'
                    WHEN p.status = 'PENDING' THEN 'Chờ duyệt'
                    WHEN p.status = 'ACTIVE' THEN 'Đang bán'
                    ELSE p.status
                END AS "statusDisplay",
                p.status,
                p.is_featured AS "isFeatured",
                p.is_flash_sale AS "isFlashSale",
                p.video_url AS "videoUrl",
                p.image_url AS "imageUrl",
                p.images,
                p.seo_metadata AS "seoMetadata",
                p.sales_config AS "salesConfig",
                p.colors,
                p.capacities,
                p.promotions,
                p.badge,
                p.rating,
                p.review_count AS "reviewCount",
                p.favorite_count AS "favoriteCount",
                p.version,
                p.created_at AS "createdAt",
                p.updated_at AS "updatedAt",
                p.options,
                COALESCE(
                    jsonb_agg(
                        DISTINCT jsonb_build_object(
                            'id', pv.id::text,
                            'sku', pv.sku,
                            'colorName', pv.color_name,
                            'colorCode', pv.color_code,
                            'storage', pv.storage,
                            'ram', pv.ram,
                            'configuration', pv.configuration,
                            'specs', pv.specs,
                            'imageUrl', pv.image_url,
                            'images', pv.images,
                            'price', pv.price,
                            'salePrice', pv.sale_price,
                            'compareAtPrice', pv.compare_at_price,
                            'stockQuantity', pv.stock_quantity,
                            'isDefault', pv.is_default,
                            'status', pv.status,
                            'attributes', pv.attributes
                        )
                    ) FILTER (WHERE pv.id IS NOT NULL AND pv.deleted_at IS NULL),
                    '[]'::jsonb
                ) AS variants
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN categories sc ON sc.id = p.subcategory_id
            LEFT JOIN product_variants pv ON pv.product_id = p.id AND pv.deleted_at IS NULL
            {where_sql}
            GROUP BY p.id, c.name, sc.name
            ORDER BY p.created_at DESC
            {pagination_sql}
            """
        ),
        params,
    )
    rows = [dict(row._mapping) for row in result]
    if rows:
        product_ids = [UUID(item["id"]) for item in rows]
        bundle_rows = (
            await session.execute(
                text(
                    """
                    SELECT pb.product_id::text AS product_id, p.sku
                    FROM product_bundles pb
                    JOIN products p ON p.id = pb.bundled_product_id
                    WHERE pb.product_id IN :ids
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": product_ids},
            )
        ).mappings().all()
        accessory_rows = (
            await session.execute(
                text(
                    """
                    SELECT pa.product_id::text AS product_id, p.id::text AS accessory_id, p.sku, p.name, p.image_url AS image_url
                    FROM product_accessories pa
                    JOIN products p ON p.id = pa.accessory_product_id
                    WHERE pa.product_id IN :ids
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": product_ids},
            )
        ).mappings().all()
        service_rows = (
            await session.execute(
                text(
                    """
                    SELECT pas.product_id::text AS product_id, s.id::text AS service_id, s.code, s.name,
                           s.service_type, s.attribute_group, s.duration_months, s.price_mode,
                           s.fixed_price, s.percent_value, s.base_amount
                    FROM product_attached_services pas
                    JOIN attached_services s ON s.id = pas.service_id
                    WHERE pas.product_id IN :ids
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": product_ids},
            )
        ).mappings().all()
        service_lookup: dict[str, list[dict]] = {}
        for service in service_rows:
            service_lookup.setdefault(service["product_id"], []).append(
                {
                    "serviceId": service["service_id"],
                    "code": service["code"],
                    "name": service["name"],
                    "serviceType": service["service_type"],
                    "attributeGroup": service["attribute_group"],
                    "durationMonths": service["duration_months"],
                    "priceMode": service["price_mode"],
                    "fixedPrice": service["fixed_price"],
                    "percentValue": service["percent_value"],
                    "baseAmount": service["base_amount"],
                }
            )
        bundles: dict[str, list[str]] = {}
        accessories: dict[str, list[str]] = {}
        accessory_lookup: dict[str, list[dict]] = {}
        for item in bundle_rows:
            bundles.setdefault(item["product_id"], []).append(item["sku"])
        for item in accessory_rows:
            accessories.setdefault(item["product_id"], []).append(item["sku"])
            accessory_lookup.setdefault(item["product_id"], []).append(
                {
                    "productId": item["accessory_id"],
                    "sku": item["sku"],
                    "name": item["name"],
                    "imageUrl": item["image_url"],
                }
            )
        for item in rows:
            sales_config = item.get("salesConfig") if isinstance(item.get("salesConfig"), dict) else {}
            offers = sales_config.get("accessoryOffers") if isinstance(sales_config.get("accessoryOffers"), list) else []
            resolved_accessory_by_id = {
                accessory["productId"]: accessory for accessory in accessory_lookup.get(item["id"], [])
            }
            accessory_offers = []
            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                product_id = str(offer.get("productId") or "")
                accessory_meta = resolved_accessory_by_id.get(product_id, {})
                accessory_offers.append(
                    {
                        **offer,
                        "productId": product_id,
                        "productName": accessory_meta.get("name", ""),
                        "productSku": accessory_meta.get("sku", ""),
                        "imageUrl": accessory_meta.get("imageUrl", ""),
                    }
                )
            item["salesConfig"] = {
                **sales_config,
                "bundleRefs": bundles.get(item["id"], []),
                "accessoryRefs": accessories.get(item["id"], []),
                "accessoryOffers": accessory_offers,
                "attachedServices": service_lookup.get(item["id"], sales_config.get("attachedServices", [])),
            }
    if cursor:
        paged = rows
        return {"items": paged, "nextCursor": paged[-1]["id"] if len(paged) == limit else None, "limit": limit}
    if page is None:
        return rows
    return {"items": rows, "totalRecords": total or 0, "totalPages": ((total or 0) + limit - 1) // limit, "page": page, "limit": limit}


@router.get("/products/suggestions", dependencies=[Depends(require_permission("product:read"))])
async def suggest_admin_products(
    search: str = Query(default="", max_length=120),
    limit: int = Query(default=10, ge=1, le=50),
    excludeId: UUID | None = None,
    categoryId: UUID | None = None,
    brandId: UUID | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                p.id::text,
                p.sku,
                p.name,
                p.image_url AS "imageUrl",
                p.status,
                p.category_id::text AS "categoryId",
                p.brand_id::text AS "brandId",
                c.name AS "categoryName",
                b.name AS "brandName"
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN brands b ON b.id = p.brand_id
            WHERE (:exclude_id IS NULL OR p.id <> :exclude_id)
              AND (:category_id IS NULL OR p.category_id = :category_id OR p.subcategory_id = :category_id)
              AND (:brand_id IS NULL OR p.brand_id = :brand_id)
              AND (
                :search = ''
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(p.sku) LIKE LOWER(:pattern)
                OR LOWER(p.brand) LIKE LOWER(:pattern)
              )
            ORDER BY p.status = 'ACTIVE' DESC, p.name
            LIMIT :limit
            """
        ),
        {
            "search": search.strip(),
            "pattern": f"%{search.strip()}%",
            "limit": limit,
            "exclude_id": excludeId,
            "category_id": categoryId,
            "brand_id": brandId,
        },
    )
    return [dict(row._mapping) for row in result]


@router.get("/attached-services", dependencies=[Depends(require_permission("product:read"))])
async def list_attached_services(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, code, name, service_type AS "serviceType",
                   attribute_group AS "attributeGroup", duration_months AS "durationMonths",
                   price_mode AS "priceMode", fixed_price AS "fixedPrice",
                   percent_value AS "percentValue", base_amount AS "baseAmount",
                   is_active AS "isActive", metadata, created_at AS "createdAt", updated_at AS "updatedAt"
            FROM attached_services
            ORDER BY service_type, attribute_group NULLS LAST, name
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.post("/attached-services", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("product:create"))])
async def create_attached_service(payload: AttachedServicePayload, session: AsyncSession = Depends(get_session)) -> dict:
    service_id = uuid4()
    price_mode = "TIERED_AMOUNT" if payload.serviceType == "PRODUCT_SERVICE" else payload.priceMode
    fixed_price = 0 if payload.serviceType == "PRODUCT_SERVICE" else payload.fixedPrice
    percent_value = 0 if payload.serviceType == "PRODUCT_SERVICE" else payload.percentValue
    base_amount = 0 if payload.serviceType == "PRODUCT_SERVICE" else payload.baseAmount
    await session.execute(
        text(
            """
            INSERT INTO attached_services (
                id, code, name, service_type, attribute_group, duration_months,
                price_mode, fixed_price, percent_value, base_amount, is_active, metadata
            )
            VALUES (
                :id, :code, :name, :service_type, :attribute_group, :duration_months,
                :price_mode, :fixed_price, :percent_value, :base_amount, :is_active, CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "id": service_id,
            "code": payload.code.strip().upper(),
            "name": payload.name.strip(),
            "service_type": payload.serviceType,
            "attribute_group": payload.attributeGroup or None,
            "duration_months": payload.durationMonths,
            "price_mode": price_mode,
            "fixed_price": fixed_price,
            "percent_value": percent_value,
            "base_amount": base_amount,
            "is_active": payload.isActive,
            "metadata": json.dumps(payload.metadata),
        },
    )
    await session.commit()
    return {"id": str(service_id)}


@router.patch("/attached-services/{service_id}", dependencies=[Depends(require_permission("product:update"))])
async def update_attached_service(service_id: UUID, payload: AttachedServicePayload, session: AsyncSession = Depends(get_session)) -> dict:
    price_mode = "TIERED_AMOUNT" if payload.serviceType == "PRODUCT_SERVICE" else payload.priceMode
    fixed_price = 0 if payload.serviceType == "PRODUCT_SERVICE" else payload.fixedPrice
    percent_value = 0 if payload.serviceType == "PRODUCT_SERVICE" else payload.percentValue
    base_amount = 0 if payload.serviceType == "PRODUCT_SERVICE" else payload.baseAmount
    result = await session.execute(
        text(
            """
            UPDATE attached_services
            SET code = :code, name = :name, service_type = :service_type,
                attribute_group = :attribute_group, duration_months = :duration_months,
                price_mode = :price_mode, fixed_price = :fixed_price,
                percent_value = :percent_value, base_amount = :base_amount,
                is_active = :is_active, metadata = CAST(:metadata AS jsonb), updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": service_id,
            "code": payload.code.strip().upper(),
            "name": payload.name.strip(),
            "service_type": payload.serviceType,
            "attribute_group": payload.attributeGroup or None,
            "duration_months": payload.durationMonths,
            "price_mode": price_mode,
            "fixed_price": fixed_price,
            "percent_value": percent_value,
            "base_amount": base_amount,
            "is_active": payload.isActive,
            "metadata": json.dumps(payload.metadata),
        },
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy dịch vụ.")
    await session.commit()
    return {"ok": True}


@router.delete("/attached-services/{service_id}", dependencies=[Depends(require_permission("product:update"))])
async def deactivate_attached_service(service_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(
        text("UPDATE attached_services SET is_active = FALSE, updated_at = NOW() WHERE id = :id"),
        {"id": service_id},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy dịch vụ.")
    await session.commit()
    return {"ok": True, "action": "deactivated"}


async def process_product_import_job(job_id: UUID, csv_text: str) -> None:
    async with AsyncSessionFactory() as session:
        try:
            rows = list(csv.DictReader(csv_text.splitlines()))
            await session.execute(
                text("UPDATE product_import_jobs SET status = 'PROCESSING', total_rows = :total, updated_at = NOW() WHERE id = :id"),
                {"id": job_id, "total": len(rows)},
            )
            await session.commit()
            imported = 0
            failed = 0
            for row in rows:
                try:
                    product_id = uuid4()
                    name = (row.get("name") or "").strip()
                    if not name:
                        failed += 1
                        continue
                    specs, seo_metadata, sales_config = extract_product_metadata({
                        "_seoTitle": row.get("seoTitle") or "",
                        "_seoDescription": row.get("seoDescription") or "",
                        "_seoSlug": row.get("seoSlug") or "",
                    })
                    await session.execute(
                        text(
                            """
                            INSERT INTO products (
                                id, sku, name, slug, category, brand, description, specifications,
                                seo_metadata, sales_config, price, sale_price, stock_quantity,
                                image_url, images, colors, capacities, promotions, status
                            )
                            VALUES (
                                :id, :sku, :name, :slug, :category, :brand, :description, '{}'::jsonb,
                                CAST(:seo_metadata AS jsonb), CAST(:sales_config AS jsonb), :price,
                                :sale_price, 0, :image_url, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
                                '[]'::jsonb, :status
                            )
                            """
                        ),
                        {
                            "id": product_id,
                            "sku": f"SKU-{product_id.hex[:10].upper()}",
                            "name": name,
                            "slug": f"{slugify(name)}-{product_id.hex[:6]}",
                            "category": row.get("category") or "ACCESSORY",
                            "brand": row.get("brand") or "Khac",
                            "description": row.get("description") or "",
                            "seo_metadata": json.dumps(seo_metadata),
                            "sales_config": json.dumps(persisted_sales_config(sales_config)),
                            "price": float(row.get("price") or 0),
                            "sale_price": float(row["discountPrice"]) if row.get("discountPrice") else None,
                            "image_url": row.get("imageUrl") or None,
                            "status": normalize_status(row.get("status") or "DRAFT"),
                        },
                    )
                    imported += 1
                except Exception:
                    failed += 1
                await session.execute(
                    text(
                        """
                        UPDATE product_import_jobs
                        SET processed_rows = processed_rows + 1,
                            imported_rows = :imported,
                            failed_rows = :failed,
                            updated_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {"id": job_id, "imported": imported, "failed": failed},
                )
                await session.commit()
            await session.execute(
                text("UPDATE product_import_jobs SET status = 'COMPLETED', updated_at = NOW() WHERE id = :id"),
                {"id": job_id},
            )
            await session.commit()
        except Exception as exc:
            await session.execute(
                text("UPDATE product_import_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
                {"id": job_id, "error": str(exc)[:1000]},
            )
            await session.commit()


async def upsert_product_variants(
    session: AsyncSession,
    product_id: UUID,
    variants_payload: list[ProductVariantPayload],
    product_name: str,
    default_price: float = 0,
    default_sale_price: float | None = None,
    default_stock: int = 0,
) -> None:
    # 1. Fetch product options to validate attributes
    product_row = (
        await session.execute(
            text("SELECT options, sku, status, parent_product_id FROM products WHERE id = :product_id"),
            {"product_id": product_id}
        )
    ).mappings().first()
    if not product_row:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    options = product_row["options"] or []
    product_status = product_row.get("status")
    parent_product_id = product_row.get("parent_product_id")
    is_revision = (product_status == "REVISION_DRAFT")
    
    # 2. Enforce flat variants and simple product default variant auto-generation
    if not variants_payload:
        default_sku = f"{slugify(product_name).upper()}-DEFAULT"
        if len(default_sku) > 120:
            default_sku = default_sku[:120]
        compare_at_price = default_price if default_sale_price is not None and default_price > default_sale_price else None
        default_var = ProductVariantPayload(
            sku=default_sku,
            price=default_sale_price if default_sale_price is not None else default_price,
            stockQuantity=default_stock,
            isDefault=True,
            isActive=True,
            status="active",
            compareAtPrice=compare_at_price,
            attributes={}
        )
        variants_payload = [default_var]

    # Validate SKU duplicate in payload
    sku_list = [v.sku.strip() for v in variants_payload if v.sku]
    if len(sku_list) != len(set(sku_list)):
        raise HTTPException(status_code=400, detail="Trùng lặp SKU trong danh sách biến thể gửi lên.")

    # Validate options matching attributes
    options_dict = {opt["name"].lower(): [v.lower() for v in opt["values"]] for opt in options if "name" in opt and "values" in opt}
    for var in variants_payload:
        var_attrs = var.attributes or {}
        for k, v in var_attrs.items():
            if k.lower() not in options_dict:
                raise HTTPException(
                    status_code=400,
                    detail=f"Thuộc tính '{k}' của biến thể không nằm trong các lựa chọn của sản phẩm."
                )
            if str(v).lower() not in options_dict[k.lower()]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Giá trị '{v}' của thuộc tính '{k}' không hợp lệ."
                )
        if options:
            for opt in options:
                opt_name = opt.get("name", "")
                if opt_name not in var_attrs:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Biến thể thiếu thuộc tính '{opt_name}' yêu cầu bởi sản phẩm."
                    )

    # Validate default variant constraints
    default_count = sum(1 for v in variants_payload if v.isDefault)
    if default_count == 0:
        variants_payload[0].isDefault = True
    elif default_count > 1:
        raise HTTPException(
            status_code=400,
            detail="Mỗi sản phẩm chỉ được có một biến thể mặc định.",
            headers={"x-error-code": "MULTIPLE_DEFAULT_VARIANTS"}
        )

    # Validate unique active SKUs in DB
    for var in variants_payload:
        if not var.sku:
            continue
        sku_query = """
            SELECT pv.id FROM product_variants pv
            WHERE pv.sku = :sku 
              AND pv.deleted_at IS NULL 
              AND pv.status <> 'revision_draft'
              AND pv.product_id <> :product_id
              AND (CAST(:parent_product_id AS UUID) IS NULL OR pv.product_id <> CAST(:parent_product_id AS UUID))
              AND (CAST(:id AS UUID) IS NULL OR pv.id <> CAST(:id AS UUID))
        """
        existing = (
            await session.execute(
                text(sku_query),
                {
                    "sku": var.sku.strip(),
                    "id": var.id,
                    "product_id": product_id,
                    "parent_product_id": parent_product_id,
                }
            )
        ).scalar()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"SKU '{var.sku}' đã được sử dụng bởi một biến thể khác đang hoạt động."
            )

    COLOR_CODE_FALLBACK = {
        "đen": "#000000", "black": "#000000",
        "trắng": "#FFFFFF", "white": "#FFFFFF",
        "đỏ": "#FF0000", "red": "#FF0000",
        "xanh lá": "#00FF00", "green": "#00FF00",
        "xanh dương": "#0000FF", "blue": "#0000FF",
        "vàng": "#FFFF00", "yellow": "#FFFF00",
        "cam": "#FFA500", "orange": "#FFA500",
        "hồng": "#FFC0CB", "pink": "#FFC0CB",
        "xám": "#808080", "gray": "#808080", "grey": "#808080",
        "tím": "#800080", "purple": "#800080",
        "bạc": "#C0C0C0", "silver": "#C0C0C0",
        "vàng hồng": "#B76E79", "rose gold": "#B76E79"
    }

    db_variants = (
        await session.execute(
            text("SELECT id FROM product_variants WHERE product_id = :product_id AND deleted_at IS NULL"),
            {"product_id": product_id}
        )
    ).scalars().all()
    
    payload_ids = {var.id for var in variants_payload if var.id}
    to_delete_ids = [vid for vid in db_variants if vid not in payload_ids]
    
    # Enforce at least one variant remaining active
    if len(variants_payload) == 0:
        raise HTTPException(
            status_code=400,
            detail="Sản phẩm phải có ít nhất một biến thể.",
            headers={"x-error-code": "CANNOT_DELETE_LAST_VARIANT"}
        )

    default_sku_for_parent = None

    for var in variants_payload:
        color_val = None
        storage_val = None
        ram_val = None
        config_val = None
        
        var_attrs = var.attributes or {}
        for k, v in var_attrs.items():
            k_lower = k.lower()
            if k_lower in {"color", "màu", "màu sắc"}:
                color_val = str(v)
            elif k_lower in {"storage", "dung lượng", "bộ nhớ"}:
                storage_val = str(v)
            elif k_lower in {"ram", "bộ nhớ trong"}:
                ram_val = str(v)
            elif k_lower in {"configuration", "cấu hình", "phiên bản"}:
                config_val = str(v)
                
        color_code = None
        if color_val:
            color_code = COLOR_CODE_FALLBACK.get(color_val.lower(), "#CCCCCC")

        db_price = var.price
        db_sale_price = None
        db_compare_at_price = None
        if var.compareAtPrice is not None and var.compareAtPrice > 0:
            db_price = var.compareAtPrice
            db_sale_price = var.price
            db_compare_at_price = var.compareAtPrice

        if var.isDefault:
            default_sku_for_parent = var.sku

        specs = dict(var_attrs)

        if var.id and var.id in db_variants:
            await session.execute(
                text(
                    """
                    UPDATE product_variants
                    SET sku = :sku,
                        color_name = :color_name,
                        color_code = :color_code,
                        storage = :storage,
                        ram = :ram,
                        configuration = :configuration,
                        specs = CAST(:specs AS jsonb),
                        image_url = :image_url,
                        images = CAST(:images AS jsonb),
                        price = :price,
                        sale_price = :sale_price,
                        compare_at_price = :compare_at_price,
                        stock_quantity = :stock_quantity,
                        is_active = :is_active,
                        is_default = :is_default,
                        status = :status,
                        attributes = CAST(:attributes AS jsonb),
                        updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {
                    "id": var.id,
                    "sku": var.sku.strip() if var.sku else f"SKU-{uuid4().hex[:10].upper()}",
                    "color_name": color_val or var.colorName,
                    "color_code": color_code or var.colorCode,
                    "storage": storage_val or var.storage,
                    "ram": ram_val or var.ram,
                    "configuration": config_val or var.configuration,
                    "specs": json.dumps(specs),
                    "image_url": var.imageUrl,
                    "images": json.dumps(var.images or []),
                    "price": db_price,
                    "sale_price": db_sale_price,
                    "compare_at_price": db_compare_at_price,
                    "stock_quantity": var.stockQuantity,
                    "is_active": var.isActive,
                    "is_default": var.isDefault,
                    "status": "revision_draft" if is_revision else var.status,
                    "attributes": json.dumps(var_attrs)
                }
            )
        else:
            new_var_id = var.id if var.id and var.id in db_variants else uuid4()
            await session.execute(
                text(
                    """
                    INSERT INTO product_variants (
                        id, product_id, sku, color_name, color_code, storage, ram, configuration,
                        specs, image_url, images, price, sale_price, compare_at_price, stock_quantity,
                        is_active, is_default, status, attributes, parent_variant_id, created_at, updated_at
                    )
                    VALUES (
                        :id, :product_id, :sku, :color_name, :color_code, :storage, :ram, :configuration,
                        CAST(:specs AS jsonb), :image_url, CAST(:images AS jsonb), :price, :sale_price, :compare_at_price, :stock_quantity,
                        :is_active, :is_default, :status, CAST(:attributes AS jsonb), :parent_variant_id, NOW(), NOW()
                    )
                    """
                ),
                {
                    "id": new_var_id,
                    "product_id": product_id,
                    "sku": var.sku.strip() if var.sku else f"SKU-{new_var_id.hex[:10].upper()}",
                    "color_name": color_val or var.colorName,
                    "color_code": color_code or var.colorCode,
                    "storage": storage_val or var.storage,
                    "ram": ram_val or var.ram,
                    "configuration": config_val or var.configuration,
                    "specs": json.dumps(specs),
                    "image_url": var.imageUrl,
                    "images": json.dumps(var.images or []),
                    "price": db_price,
                    "sale_price": db_sale_price,
                    "compare_at_price": db_compare_at_price,
                    "stock_quantity": var.stockQuantity,
                    "is_active": var.isActive,
                    "is_default": var.isDefault,
                    "status": "revision_draft" if is_revision else var.status,
                    "attributes": json.dumps(var_attrs),
                    "parent_variant_id": var.id if var.id and var.id not in db_variants else None,
                }
            )

    if to_delete_ids:
        await session.execute(
            text(
                """
                UPDATE product_variants
                SET deleted_at = NOW(),
                    status = 'deleted',
                    is_active = FALSE
                WHERE id IN :ids
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": to_delete_ids}
        )

    if default_sku_for_parent:
        await session.execute(
            text("UPDATE products SET sku = :sku WHERE id = :product_id"),
            {"sku": default_sku_for_parent, "product_id": product_id}
        )


async def create_product_revision(
    session: AsyncSession,
    product_id: UUID,
    payload: ProductPayload,
    clean_specs: dict,
    seo_metadata: dict,
    sales_config: dict,
    category: str,
    brand: str,
) -> dict:
    revision_id = uuid4()
    clean_options = normalize_product_options(payload.options)
    await session.execute(
        text(
            """
            INSERT INTO products (
                id, parent_product_id, sku, name, slug, category, brand, category_id, subcategory_id, brand_id,
                description, specifications, seo_metadata, sales_config, price, sale_price, stock_quantity, image_url,
                images, video_url, colors, capacities, promotions, status, is_featured, is_flash_sale, options
            )
            VALUES (
                :id, :parent_product_id, :sku, :name, :slug, :category, :brand, :category_id, :subcategory_id, :brand_id,
                :description, CAST(:specifications AS jsonb), CAST(:seo_metadata AS jsonb), CAST(:sales_config AS jsonb),
                :price, :sale_price, 0, :image_url, CAST(:images AS jsonb), :video_url,
                '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, 'REVISION_DRAFT', :is_featured, :is_flash_sale,
                CAST(:options AS jsonb)
            )
            """
        ),
        {
            "id": revision_id,
            "parent_product_id": product_id,
            "sku": f"REV-{revision_id.hex[:10].upper()}",
            "name": payload.name,
            "slug": f"{slugify(payload.name)}-revision-{revision_id.hex[:6]}",
            "category": category,
            "brand": brand,
            "category_id": payload.categoryId,
            "subcategory_id": payload.subcategoryId,
            "brand_id": payload.brandId,
            "description": payload.description or "",
            "specifications": json.dumps(clean_specs),
            "seo_metadata": json.dumps(seo_metadata),
            "sales_config": json.dumps(persisted_sales_config(sales_config)),
            "price": payload.price,
            "sale_price": payload.discountPrice,
            "image_url": payload.imageUrl,
            "images": json.dumps(payload.images),
            "video_url": payload.videoUrl,
            "is_featured": payload.isFeatured,
            "is_flash_sale": payload.isFlashSale,
            "options": json.dumps(clean_options),
        },
    )
    await upsert_product_variants(session, revision_id, payload.variants, payload.name, payload.price, payload.discountPrice, payload.stock)
    await sync_parent_price_from_variants(session, revision_id)
    await sync_product_relations(session, revision_id, sales_config)
    await session.commit()
    return {"ok": True, "revisionId": str(revision_id), "status": "REVISION_DRAFT"}


@router.post("/products/import", dependencies=[Depends(require_permission("product:create"))])
async def import_products(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ nhập sản phẩm từ tệp CSV.")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Tệp CSV quá lớn.")
    job_id = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO product_import_jobs (id, source_filename, status)
            VALUES (:id, :source_filename, 'PENDING')
            """
        ),
        {"id": job_id, "source_filename": file.filename},
    )
    await session.commit()
    background_tasks.add_task(process_product_import_job, job_id, content.decode("utf-8-sig"))
    return {"jobId": str(job_id), "status": "PENDING"}


@router.get("/products/import-jobs", dependencies=[Depends(require_permission("product:read"))])
async def list_product_import_jobs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, source_filename AS "sourceFilename", status, total_rows AS "totalRows",
                   processed_rows AS "processedRows", imported_rows AS "importedRows",
                   failed_rows AS "failedRows", error_message AS "errorMessage",
                   created_at AS "createdAt", updated_at AS "updatedAt"
            FROM product_import_jobs
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def process_product_export_job(job_id: UUID, filters: dict) -> None:
    async with AsyncSessionFactory() as session:
        try:
            await session.execute(text("UPDATE product_export_jobs SET status = 'PROCESSING', updated_at = NOW() WHERE id = :id"), {"id": job_id})
            result = await session.execute(
                text(
                    """
                    SELECT id::text, sku, name, brand, category, price, sale_price AS "discountPrice",
                           stock_quantity AS stock, status, seo_metadata, sales_config
                    FROM products
                    WHERE (:search = '' OR LOWER(name) LIKE LOWER(:pattern) OR LOWER(sku) LIKE LOWER(:pattern) OR LOWER(brand) LIKE LOWER(:pattern))
                      AND (:status = '' OR status = :status)
                    ORDER BY created_at DESC
                    """
                ),
                {
                    "search": filters.get("search", ""),
                    "pattern": f"%{filters.get('search', '')}%",
                    "status": filters.get("status", ""),
                },
            )
            rows = [dict(row._mapping) for row in result]
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["id", "sku", "name", "brand", "category", "price", "discountPrice", "stock", "status", "seoTitle", "seoDescription", "seoSlug"])
            writer.writeheader()
            for row in rows:
                seo = row.get("seo_metadata") if isinstance(row.get("seo_metadata"), dict) else {}
                sales = row.get("sales_config") if isinstance(row.get("sales_config"), dict) else {}
                writer.writerow({
                    "id": row.get("id"),
                    "sku": row.get("sku"),
                    "name": row.get("name"),
                    "brand": row.get("brand"),
                    "category": row.get("category"),
                    "price": row.get("price"),
                    "discountPrice": row.get("discountPrice"),
                    "stock": row.get("stock"),
                    "status": row.get("status"),
                    "seoTitle": seo.get("title", ""),
                    "seoDescription": seo.get("description", ""),
                    "seoSlug": seo.get("slug", ""),
                })
            export_dir = Path("exports")
            export_dir.mkdir(exist_ok=True)
            export_path = export_dir / f"products-{job_id}.csv"
            export_path.write_text(output.getvalue(), encoding="utf-8-sig")
            download_url = f"/exports/{export_path.name}"
            await session.execute(
                text(
                    """
                    UPDATE product_export_jobs
                    SET status = 'COMPLETED', total_rows = :total, processed_rows = :total,
                        file_path = :file_path, download_url = :download_url,
                        expires_at = :expires_at, updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {
                    "id": job_id,
                    "total": len(rows),
                    "file_path": str(export_path),
                    "download_url": download_url,
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
                },
            )
            await session.commit()
        except Exception as exc:
            await session.execute(
                text("UPDATE product_export_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
                {"id": job_id, "error": str(exc)[:1000]},
            )
            await session.commit()


@router.post("/products/export", dependencies=[Depends(require_permission("product:read"))])
async def export_products(
    background_tasks: BackgroundTasks,
    filters: dict | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    job_id = uuid4()
    export_filters = filters or {}
    await session.execute(
        text("INSERT INTO product_export_jobs (id, status, filters) VALUES (:id, 'PENDING', CAST(:filters AS jsonb))"),
        {"id": job_id, "filters": json.dumps(export_filters)},
    )
    await session.commit()
    background_tasks.add_task(process_product_export_job, job_id, export_filters)
    return {"jobId": str(job_id), "status": "PENDING"}


@router.get("/products/export-jobs", dependencies=[Depends(require_permission("product:read"))])
async def list_product_export_jobs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, status, filters, total_rows AS "totalRows", processed_rows AS "processedRows",
                   download_url AS "downloadUrl", expires_at AS "expiresAt", error_message AS "errorMessage",
                   created_at AS "createdAt", updated_at AS "updatedAt"
            FROM product_export_jobs
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.get("/products/kpis", dependencies=[Depends(require_permission("product:read"))])
async def product_catalog_kpis(session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(
        text(
            """
            SELECT
                AVG(EXTRACT(EPOCH FROM (active_product.updated_at - draft_product.created_at)) / 3600) AS time_to_market_hours,
                COUNT(*) FILTER (WHERE active_product.status = 'DRAFT' AND active_product.updated_at < NOW() - INTERVAL '30 days') AS orphaned_products,
                COUNT(*) FILTER (WHERE active_product.status = 'INACTIVE') AS inactive_products,
                COUNT(*) FILTER (WHERE active_product.status = 'ACTIVE') AS active_products
            FROM products active_product
            LEFT JOIN products draft_product ON draft_product.id = active_product.id
            """
        )
    )
    row = dict(result.mappings().one())
    import_jobs = (
        await session.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(imported_rows), 0) AS imported_rows,
                    COALESCE(SUM(total_rows), 0) AS total_rows
                FROM product_import_jobs
                WHERE status IN ('COMPLETED', 'FAILED')
                """
            )
        )
    ).mappings().one()
    total_rows = int(import_jobs["total_rows"] or 0)
    return {
        "timeToMarketHours": float(row["time_to_market_hours"] or 0),
        "catalogAccuracyRate": 1 - (int(row["inactive_products"] or 0) / max(int(row["active_products"] or 0) + int(row["inactive_products"] or 0), 1)),
        "orphanedProducts": int(row["orphaned_products"] or 0),
        "importSuccessRate": (int(import_jobs["imported_rows"] or 0) / total_rows) if total_rows else 1,
    }


@router.get("/products/{product_id}/audit-logs", dependencies=[Depends(require_permission("product:read"))])
async def list_product_audit_logs(product_id: UUID, session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, product_id::text AS "productId", actor_id::text AS "actorId",
                   action, old_value AS "oldValue", new_value AS "newValue", created_at AS "createdAt"
            FROM product_audit_logs
            WHERE product_id = :product_id
            ORDER BY created_at DESC
            LIMIT 100
            """
        ),
        {"product_id": product_id},
    )
    return [dict(row._mapping) for row in result]


@router.post("/products", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("product:create"))])
async def create_product(payload: ProductPayload, session: AsyncSession = Depends(get_session)) -> dict:
    product_id = uuid4()
    clean_options = normalize_product_options(payload.options)
    validate_optimized_media(payload)
    ensure_not_data_url(payload.imageUrl, "imageUrl")
    ensure_not_data_url(payload.videoUrl, "videoUrl")
    for image in payload.images:
        ensure_not_data_url(image, "images")
    await ensure_categories_not_migrating(session, [payload.categoryId, payload.subcategoryId])
    category, brand = await resolve_catalog_labels(session, payload)
    clean_specs, seo_metadata, sales_config = extract_product_metadata(payload.specifications)
    await session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, category_id, subcategory_id, brand_id,
                description, specifications, seo_metadata, sales_config, price, sale_price, stock_quantity, image_url,
                images, video_url, colors, capacities, promotions, status, is_featured, is_flash_sale, options
            )
            VALUES (
                :id, :sku, :name, :slug, :category, :brand, :category_id, :subcategory_id, :brand_id,
                :description, CAST(:specifications AS jsonb), CAST(:seo_metadata AS jsonb), CAST(:sales_config AS jsonb), :price, :sale_price, 0, :image_url,
                CAST(:images AS jsonb), :video_url, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, :status, :is_featured, :is_flash_sale,
                CAST(:options AS jsonb)
            )
            """
        ),
        {
            "id": product_id,
            "sku": f"SKU-{product_id.hex[:10].upper()}",
            "name": payload.name,
            "slug": f"{slugify(payload.name)}-{product_id.hex[:6]}",
            "category": category,
            "brand": brand,
            "category_id": payload.categoryId,
            "subcategory_id": payload.subcategoryId,
            "brand_id": payload.brandId,
            "description": payload.description or "",
            "specifications": json.dumps(clean_specs),
            "seo_metadata": json.dumps(seo_metadata),
            "sales_config": json.dumps(persisted_sales_config(sales_config)),
            "price": payload.price,
            "sale_price": payload.discountPrice,
            "image_url": payload.imageUrl,
            "images": json.dumps(payload.images),
            "video_url": payload.videoUrl,
            "status": normalize_status(payload.status),
            "is_featured": payload.isFeatured,
            "is_flash_sale": payload.isFlashSale,
            "options": json.dumps(clean_options),
        },
    )
    await upsert_product_variants(session, product_id, payload.variants, payload.name, payload.price, payload.discountPrice, payload.stock)
    await sync_parent_price_from_variants(session, product_id)
    await sync_product_relations(session, product_id, sales_config)
    await audit_product_event(session, product_id, "PRODUCT_CREATED", new_value={"name": payload.name, "status": normalize_status(payload.status)})
    await session.commit()
    return {"id": str(product_id)}


@router.patch("/products/{product_id}", dependencies=[Depends(require_permission("product:update"))])
async def update_product(product_id: UUID, payload: ProductPayload, session: AsyncSession = Depends(get_session)) -> dict:
    clean_options = normalize_product_options(payload.options)
    validate_optimized_media(payload)
    ensure_not_data_url(payload.imageUrl, "imageUrl")
    ensure_not_data_url(payload.videoUrl, "videoUrl")
    for image in payload.images:
        ensure_not_data_url(image, "images")
    await ensure_categories_not_migrating(session, [payload.categoryId, payload.subcategoryId])
    category, brand = await resolve_catalog_labels(session, payload)
    clean_specs, seo_metadata, sales_config = extract_product_metadata(payload.specifications)
    current = (
        await session.execute(
            text("SELECT status, version, updated_at, name, price, sale_price, category_id, subcategory_id FROM products WHERE id = :id"),
            {"id": product_id},
        )
    ).mappings().first()
    if not current:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    await ensure_categories_not_migrating(session, [current["category_id"], current["subcategory_id"], payload.categoryId, payload.subcategoryId])
    if payload.version is not None and int(current["version"] or 0) != payload.version:
        raise HTTPException(status_code=409, detail="Sản phẩm đã được cập nhật bởi quản trị viên khác. Vui lòng tải lại trang.")
    if payload.updatedAt and payload.version is None:
        if str(current["updated_at"].isoformat())[:19] != str(payload.updatedAt)[:19]:
            raise HTTPException(status_code=409, detail="Sản phẩm đã được cập nhật bởi quản trị viên khác. Vui lòng tải lại trang.")
    if current["status"] == "ACTIVE":
        return await create_product_revision(session, product_id, payload, clean_specs, seo_metadata, sales_config, category, brand)
    if False:
        current = (
            await session.execute(
                text("SELECT updated_at FROM products WHERE id = :id"),
                {"id": product_id},
            )
        ).mappings().first()
        if not current:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
        if str(current["updated_at"].isoformat())[:19] != str(payload.updatedAt)[:19]:
            raise HTTPException(status_code=409, detail="Sản phẩm đã được cập nhật bởi quản trị viên khác. Vui lòng tải lại trang.")
    result = await session.execute(
        text(
            """
            UPDATE products
            SET name = :name,
                category = :category,
                brand = :brand,
                category_id = :category_id,
                subcategory_id = :subcategory_id,
                brand_id = :brand_id,
                description = :description,
                specifications = CAST(:specifications AS jsonb),
                seo_metadata = CAST(:seo_metadata AS jsonb),
                sales_config = CAST(:sales_config AS jsonb),
                price = :price,
                sale_price = :sale_price,
                image_url = :image_url,
                images = CAST(:images AS jsonb),
                video_url = :video_url,
                options = CAST(:options AS jsonb),
                status = :status,
                is_featured = :is_featured,
                is_flash_sale = :is_flash_sale,
                version = version + 1,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": product_id,
            "name": payload.name,
            "category": category,
            "brand": brand,
            "category_id": payload.categoryId,
            "subcategory_id": payload.subcategoryId,
            "brand_id": payload.brandId,
            "description": payload.description or "",
            "specifications": json.dumps(clean_specs),
            "seo_metadata": json.dumps(seo_metadata),
            "sales_config": json.dumps(persisted_sales_config(sales_config)),
            "price": payload.price,
            "sale_price": payload.discountPrice,
            "image_url": payload.imageUrl,
            "images": json.dumps(payload.images),
            "video_url": payload.videoUrl,
            "options": json.dumps(clean_options),
            "status": normalize_status(payload.status),
            "is_featured": payload.isFeatured,
            "is_flash_sale": payload.isFlashSale,
        },
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    await upsert_product_variants(session, product_id, payload.variants, payload.name, payload.price, payload.discountPrice, payload.stock)
    await sync_parent_price_from_variants(session, product_id)
    if normalize_status(payload.status) == "INACTIVE":
        await session.execute(text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :product_id"), {"product_id": product_id})
    await sync_product_relations(session, product_id, sales_config)
    await audit_product_event(
        session,
        product_id,
        "PRODUCT_UPDATED",
        old_value={"name": current["name"], "price": str(current["price"]), "salePrice": str(current["sale_price"])},
        new_value={"name": payload.name, "price": payload.price, "salePrice": payload.discountPrice, "status": normalize_status(payload.status)},
    )
    await session.commit()
    return {"ok": True}


async def merge_revision_variants(session: AsyncSession, *, parent_id: UUID, revision_id: UUID) -> None:
    has_order_item_variant_id = (
        await session.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'order_items' AND column_name = 'variant_id'
                )
                """
            )
        )
    ).scalar()
    live_rows = (
        await session.execute(
            text(
                """
                SELECT id, sku, is_default
                FROM product_variants
                WHERE product_id = :parent_id AND deleted_at IS NULL
                FOR UPDATE
                """
            ),
            {"parent_id": parent_id},
        )
    ).mappings().all()
    revision_rows = (
        await session.execute(
            text(
                """
                SELECT id, parent_variant_id, sku, color_name, color_code, storage, ram, configuration,
                       specs, image_url, images, price, sale_price, compare_at_price,
                       stock_quantity, is_active, is_default, status, attributes
                FROM product_variants
                WHERE product_id = :revision_id AND deleted_at IS NULL
                ORDER BY created_at ASC
                """
            ),
            {"revision_id": revision_id},
        )
    ).mappings().all()
    active_revision_rows = [row for row in revision_rows if row["is_active"] is not False and str(row["status"]).lower() not in {"deleted", "archived", "inactive"}]
    if not active_revision_rows:
        raise HTTPException(status_code=400, detail="Không thể áp dụng bản chỉnh sửa nếu không có ít nhất một biến thể đang hoạt động.")

    live_by_id = {row["id"]: row for row in live_rows}
    live_by_sku = {str(row["sku"] or "").strip(): row for row in live_rows if str(row["sku"] or "").strip()}
    revision_skus = {str(row["sku"] or "").strip() for row in revision_rows if str(row["sku"] or "").strip()}
    kept_live_ids: set[UUID] = set()

    for revision in revision_rows:
        sku = str(revision["sku"] or "").strip()
        live = live_by_id.get(revision["parent_variant_id"]) if revision["parent_variant_id"] else None
        live = live or live_by_sku.get(sku)
        if live:
            kept_live_ids.add(live["id"])
            await session.execute(
                text(
                    """
                    UPDATE product_variants
                    SET parent_variant_id = NULL,
                        color_name = :color_name,
                        color_code = :color_code,
                        storage = :storage,
                        ram = :ram,
                        configuration = :configuration,
                        specs = CAST(:specs AS jsonb),
                        image_url = :image_url,
                        images = CAST(:images AS jsonb),
                        price = :price,
                        sale_price = :sale_price,
                        compare_at_price = :compare_at_price,
                        is_active = :is_active,
                        is_default = :is_default,
                        status = :status,
                        attributes = CAST(:attributes AS jsonb),
                        updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {
                    "id": live["id"],
                    "color_name": revision["color_name"],
                    "color_code": revision["color_code"],
                    "storage": revision["storage"],
                    "ram": revision["ram"],
                    "configuration": revision["configuration"],
                    "specs": json.dumps(revision["specs"] or {}),
                    "image_url": revision["image_url"],
                    "images": json.dumps(revision["images"] or []),
                    "price": revision["price"],
                    "sale_price": revision["sale_price"],
                    "compare_at_price": revision["compare_at_price"],
                    "is_active": revision["is_active"],
                    "is_default": revision["is_default"],
                    "status": "active" if revision["is_active"] is not False else "inactive",
                    "attributes": json.dumps(revision["attributes"] or {}),
                },
            )
        else:
            new_variant_id = uuid4()
            kept_live_ids.add(new_variant_id)
            await session.execute(
                text(
                    """
                    INSERT INTO product_variants (
                        id, product_id, parent_variant_id, sku, color_name, color_code, storage, ram, configuration,
                        specs, image_url, images, price, sale_price, compare_at_price, stock_quantity,
                        is_active, is_default, status, attributes, created_at, updated_at
                    )
                    VALUES (
                        :id, :parent_id, NULL, :sku, :color_name, :color_code, :storage, :ram, :configuration,
                        CAST(:specs AS jsonb), :image_url, CAST(:images AS jsonb), :price, :sale_price, :compare_at_price, :stock_quantity,
                        :is_active, :is_default, :status, CAST(:attributes AS jsonb), NOW(), NOW()
                    )
                    """
                ),
                {
                    "id": new_variant_id,
                    "parent_id": parent_id,
                    "sku": sku or f"SKU-{new_variant_id.hex[:10].upper()}",
                    "color_name": revision["color_name"],
                    "color_code": revision["color_code"],
                    "storage": revision["storage"],
                    "ram": revision["ram"],
                    "configuration": revision["configuration"],
                    "specs": json.dumps(revision["specs"] or {}),
                    "image_url": revision["image_url"],
                    "images": json.dumps(revision["images"] or []),
                    "price": revision["price"],
                    "sale_price": revision["sale_price"],
                    "compare_at_price": revision["compare_at_price"],
                    "stock_quantity": max(0, int(revision["stock_quantity"] or 0)),
                    "is_active": revision["is_active"],
                    "is_default": revision["is_default"],
                    "status": "active" if revision["is_active"] is not False else "inactive",
                    "attributes": json.dumps(revision["attributes"] or {}),
                },
            )

    kept_revision_parent_ids = {row["parent_variant_id"] for row in revision_rows if row["parent_variant_id"]}
    missing_live = [row for row in live_rows if row["id"] not in kept_revision_parent_ids and str(row["sku"] or "").strip() not in revision_skus]
    for live in missing_live:
        history_sql = """
                    SELECT
                        (SELECT COUNT(*) FROM inventory_adjustment_logs WHERE variant_id = :variant_id) AS total
                    """
        if has_order_item_variant_id:
            history_sql = """
                    SELECT
                        (SELECT COUNT(*) FROM order_items WHERE variant_id = :variant_id) +
                        (SELECT COUNT(*) FROM inventory_adjustment_logs WHERE variant_id = :variant_id) AS total
                    """
        has_history = (
            await session.execute(
                text(history_sql),
                {"variant_id": live["id"]},
            )
        ).scalar_one()
        next_status = "inactive" if int(has_history or 0) > 0 else "archived"
        await session.execute(
            text(
                """
                UPDATE product_variants
                SET is_active = FALSE,
                    is_default = FALSE,
                    status = :status,
                    deleted_at = CASE WHEN :status = 'archived' THEN NOW() ELSE deleted_at END,
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"id": live["id"], "status": next_status},
        )

    default_count = (
        await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM product_variants
                WHERE product_id = :parent_id AND deleted_at IS NULL AND is_active = TRUE AND is_default = TRUE
                """
            ),
            {"parent_id": parent_id},
        )
    ).scalar_one()
    if int(default_count or 0) != 1:
        first_active = (
            await session.execute(
                text(
                    """
                    SELECT id
                    FROM product_variants
                    WHERE product_id = :parent_id AND deleted_at IS NULL AND is_active = TRUE
                    ORDER BY created_at ASC
                    LIMIT 1
                    """
                ),
                {"parent_id": parent_id},
            )
        ).scalar()
        if not first_active:
            raise HTTPException(status_code=400, detail="Không thể áp dụng bản chỉnh sửa nếu không có ít nhất một biến thể đang hoạt động.")
        await session.execute(text("UPDATE product_variants SET is_default = FALSE WHERE product_id = :parent_id"), {"parent_id": parent_id})
        await session.execute(text("UPDATE product_variants SET is_default = TRUE WHERE id = :id"), {"id": first_active})


async def transition_product_status(
    session: AsyncSession,
    product_id: UUID,
    *,
    allowed_from: set[str],
    next_status: str,
) -> dict:
    row = (
        await session.execute(
            text(
                """
                SELECT id, parent_product_id, status, name, sku, category_id, image_url, price, sale_price,
                       subcategory_id, stock_quantity, specifications, sales_config, is_flash_sale
                FROM products
                WHERE id = :id
                FOR UPDATE
                """
            ),
            {"id": product_id},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    await ensure_categories_not_migrating(session, [row["category_id"], row["subcategory_id"]])
    current_status = str(row["status"])
    if current_status not in allowed_from:
        raise HTTPException(status_code=400, detail=f"Không thể chuyển đổi trạng thái sản phẩm từ {current_status} sang {next_status}.")
    variants = (
        await session.execute(
            text("SELECT price, sale_price, stock_quantity, is_active FROM product_variants WHERE product_id = :product_id AND deleted_at IS NULL"),
            {"product_id": product_id},
        )
    ).mappings().all()
    if next_status == "PENDING":
        missing = []
        if not row["name"]:
            missing.append("name")
        if not row["sku"]:
            missing.append("sku")
        if not row["category_id"]:
            missing.append("category")
        if not row["image_url"]:
            missing.append("imageUrl")
        if missing:
            field_names = {
                "name": "tên sản phẩm",
                "sku": "mã SKU",
                "category": "danh mục",
                "imageUrl": "ảnh đại diện"
            }
            missing_translated = [field_names.get(f, f) for f in missing]
            raise HTTPException(status_code=400, detail=f"Thiếu các trường thông tin bắt buộc trước khi gửi duyệt: {', '.join(missing_translated)}.")
    if next_status == "ACTIVE":
        variant_keys = []
        sales_config = row["sales_config"] or {}
        if isinstance(sales_config, dict):
            variant_keys = sales_config.get("variantSpecKeys") or []
        active_variants = [variant for variant in variants if variant["is_active"] is not False]
        if variant_keys and not active_variants:
            raise HTTPException(status_code=400, detail="Sản phẩm cần có ít nhất một biến thể hoạt động trước khi duyệt.")
        if active_variants:
            invalid_variant = next((variant for variant in active_variants if float(variant["sale_price"] or variant["price"] or 0) <= 0), None)
            if invalid_variant:
                raise HTTPException(status_code=400, detail="Mỗi biến thể hoạt động cần có giá hợp lệ trước khi duyệt.")
        elif float(row["sale_price"] or row["price"] or 0) <= 0:
            raise HTTPException(status_code=400, detail="Sản phẩm đơn lẻ cần có giá hợp lệ trước khi duyệt.")
        await sync_parent_price_from_variants(session, product_id)
        if row["parent_product_id"]:
            parent_id = row["parent_product_id"]
            await session.execute(
                text(
                    """
                    UPDATE products parent
                    SET name = revision.name,
                        category = revision.category,
                        brand = revision.brand,
                        category_id = revision.category_id,
                        subcategory_id = revision.subcategory_id,
                        brand_id = revision.brand_id,
                        description = revision.description,
                        specifications = revision.specifications,
                        seo_metadata = revision.seo_metadata,
                        sales_config = revision.sales_config,
                        image_url = revision.image_url,
                        images = revision.images,
                        video_url = revision.video_url,
                        options = revision.options,
                        is_featured = revision.is_featured,
                        is_flash_sale = revision.is_flash_sale,
                        version = parent.version + 1,
                        updated_at = NOW()
                    FROM products revision
                    WHERE parent.id = :parent_id AND revision.id = :revision_id
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id},
            )
            await merge_revision_variants(session, parent_id=parent_id, revision_id=product_id)
            await session.execute(text("DELETE FROM product_bundles WHERE product_id = :parent_id"), {"parent_id": parent_id})
            await session.execute(
                text(
                    """
                    INSERT INTO product_bundles (product_id, bundled_product_id)
                    SELECT :parent_id, bundled_product_id
                    FROM product_bundles
                    WHERE product_id = :revision_id
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id},
            )
            await session.execute(text("DELETE FROM product_accessories WHERE product_id = :parent_id"), {"parent_id": parent_id})
            await session.execute(
                text(
                    """
                    INSERT INTO product_accessories (product_id, accessory_product_id)
                    SELECT :parent_id, accessory_product_id
                    FROM product_accessories
                    WHERE product_id = :revision_id
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"parent_id": parent_id, "revision_id": product_id},
            )
            await sync_parent_price_from_variants(session, parent_id)
            await audit_product_event(session, parent_id, "REVISION_PUBLISHED", old_value={"revisionId": str(product_id)}, new_value={"publishedProductId": str(parent_id), "revisionStatus": "MERGED"})
            await session.execute(text("UPDATE products SET status = 'MERGED', updated_at = NOW() WHERE id = :revision_id"), {"revision_id": product_id})
            await session.commit()
            return {"ok": True, "status": "ACTIVE", "publishedProductId": str(parent_id)}
    if next_status == "ARCHIVED":
        relation_count = (
            await session.execute(
                text(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM product_bundles WHERE bundled_product_id = :id) +
                        (SELECT COUNT(*) FROM product_accessories WHERE accessory_product_id = :id) AS total
                    """
                ),
                {"id": product_id},
            )
        ).scalar_one()
        if int(relation_count or 0) > 0 or row["is_flash_sale"]:
            raise HTTPException(status_code=409, detail="Sản phẩm đang được sử dụng trong combo/phụ kiện bán kèm hoặc chương trình flash sale. Vui lòng kiểm tra lại các liên kết trước khi lưu trữ.")
    await session.execute(
        text("UPDATE products SET status = :status, updated_at = NOW() WHERE id = :id"),
        {"id": product_id, "status": next_status},
    )
    if next_status == "INACTIVE":
        await session.execute(text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :product_id"), {"product_id": product_id})
    await audit_product_event(session, product_id, "PRODUCT_STATUS_CHANGED", old_value={"status": current_status}, new_value={"status": next_status})
    await session.commit()
    return {"ok": True, "status": next_status}


@router.post("/products/{product_id}/submit", dependencies=[Depends(require_permission("product:update"))])
async def submit_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await transition_product_status(session, product_id, allowed_from={"DRAFT", "REVISION_DRAFT"}, next_status="PENDING")


@router.post("/products/{product_id}/approve", dependencies=[Depends(require_permission("product:update"))])
async def approve_product(
    product_id: UUID, 
    session: AsyncSession = Depends(get_session),
    role_code: str = Depends(get_current_role_code),
) -> dict:
    allowed = {"PENDING"}
    if role_code == "SUPER_ADMIN":
        allowed.update({"DRAFT", "REVISION_DRAFT"})
    return await transition_product_status(session, product_id, allowed_from=allowed, next_status="ACTIVE")


@router.post("/products/bulk-approve", dependencies=[Depends(require_permission("product:update"))])
async def bulk_approve_products(
    payload: ProductBulkActionPayload, 
    session: AsyncSession = Depends(get_session),
    role_code: str = Depends(get_current_role_code),
) -> dict:
    ids = payload.ids or payload.productIds or []
    updated = 0
    skipped: list[str] = []
    allowed = {"PENDING"}
    if role_code == "SUPER_ADMIN":
        allowed.update({"DRAFT", "REVISION_DRAFT"})
    for product_id in ids:
        try:
            await transition_product_status(session, product_id, allowed_from=allowed, next_status="ACTIVE")
            updated += 1
        except HTTPException:
            skipped.append(str(product_id))
    return {"ok": True, "updated": updated, "skipped": skipped}


@router.post("/products/bulk-action", dependencies=[Depends(require_permission("product:update"))])
async def product_bulk_action(
    payload: ProductBulkActionPayload, 
    session: AsyncSession = Depends(get_session),
    role_code: str = Depends(get_current_role_code),
) -> dict:
    ids = payload.productIds or payload.ids or []
    updated = 0
    skipped: list[str] = []
    allowed = {"PENDING"}
    if role_code == "SUPER_ADMIN":
        allowed.update({"DRAFT", "REVISION_DRAFT"})
    for product_id in ids:
        try:
            if payload.action == "APPROVE":
                await transition_product_status(session, product_id, allowed_from=allowed, next_status="ACTIVE")
            elif payload.action == "ARCHIVE":
                await transition_product_status(session, product_id, allowed_from={"DRAFT", "INACTIVE"}, next_status="ARCHIVED")
            elif payload.action == "DELETE":
                result = await session.execute(
                    text("UPDATE products SET status = 'INACTIVE', updated_at = NOW() WHERE id = :id AND status <> 'ARCHIVED'"),
                    {"id": product_id},
                )
                if result.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
                await session.execute(text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :id"), {"id": product_id})
                await session.commit()
            updated += 1
        except HTTPException:
            skipped.append(str(product_id))
    return {"ok": True, "action": payload.action, "updated": updated, "skipped": skipped}


@router.post("/products/{product_id}/duplicate", dependencies=[Depends(require_permission("product:create"))])
async def duplicate_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    source = (
        await session.execute(
            text("SELECT id, name FROM products WHERE id = :id"),
            {"id": product_id},
        )
    ).mappings().first()
    if not source:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")

    new_id = uuid4()
    suffix = new_id.hex[:6]
    insert_result = await session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, category_id, subcategory_id, brand_id,
                description, specifications, seo_metadata, sales_config, price, sale_price, stock_quantity, image_url,
                images, video_url, colors, capacities, promotions, status, is_featured, is_flash_sale, options
            )
            SELECT
                :new_id,
                :sku,
                CONCAT(name, ' (Copy)'),
                :slug,
                category,
                brand,
                category_id,
                subcategory_id,
                brand_id,
                description,
                specifications,
                seo_metadata,
                sales_config,
                price,
                sale_price,
                0,
                image_url,
                images,
                video_url,
                colors,
                capacities,
                promotions,
                'DRAFT',
                is_featured,
                is_flash_sale,
                options
            FROM products
            WHERE id = :source_id
            RETURNING id::text
            """
        ),
        {
            "new_id": new_id,
            "source_id": product_id,
            "sku": f"SKU-{new_id.hex[:10].upper()}",
            "slug": f"{slugify(str(source['name']))}-copy-{suffix}",
        },
    )
    if not insert_result.first():
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    await session.execute(
        text(
            """
            INSERT INTO product_variants (
                id, product_id, sku, color_name, color_code, storage, ram, configuration,
                specs, image_url, images, price, sale_price, compare_at_price, stock_quantity,
                is_active, is_default, status, attributes
            )
            SELECT
                gen_random_uuid(),
                :new_id,
                LEFT(CONCAT(sku, '-COPY-', :suffix), 120),
                color_name,
                color_code,
                storage,
                ram,
                configuration,
                specs,
                image_url,
                images,
                price,
                sale_price,
                compare_at_price,
                0,
                is_active,
                is_default,
                status,
                attributes
            FROM product_variants
            WHERE product_id = :source_id AND is_active = TRUE AND deleted_at IS NULL
            """
        ),
        {"new_id": new_id, "source_id": product_id, "suffix": suffix},
    )
    await session.execute(
        text(
            """
            INSERT INTO product_bundles (product_id, bundled_product_id)
            SELECT :new_id, bundled_product_id
            FROM product_bundles
            WHERE product_id = :source_id
            ON CONFLICT DO NOTHING
            """
        ),
        {"new_id": new_id, "source_id": product_id},
    )
    await session.execute(
        text(
            """
            INSERT INTO product_accessories (product_id, accessory_product_id)
            SELECT :new_id, accessory_product_id
            FROM product_accessories
            WHERE product_id = :source_id
            ON CONFLICT DO NOTHING
            """
        ),
        {"new_id": new_id, "source_id": product_id},
    )
    await session.commit()
    return {"id": str(new_id)}


@router.post("/products/{product_id}/archive", dependencies=[Depends(require_permission("product:update"))])
async def archive_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await transition_product_status(session, product_id, allowed_from={"DRAFT", "INACTIVE", "REVISION_DRAFT"}, next_status="ARCHIVED")


@router.delete("/products/{product_id}", dependencies=[Depends(require_permission("product:delete"))])
async def deactivate_product(product_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    product_category_row = (
        await session.execute(
            text("SELECT category_id, subcategory_id, parent_product_id, status FROM products WHERE id = :id"),
            {"id": product_id},
        )
    ).mappings().first()
    if not product_category_row:
        raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
    if product_category_row["status"] == "REVISION_DRAFT" and product_category_row["parent_product_id"]:
        await session.execute(text("DELETE FROM product_bundles WHERE product_id = :id"), {"id": product_id})
        await session.execute(text("DELETE FROM product_accessories WHERE product_id = :id"), {"id": product_id})
        await session.execute(text("DELETE FROM product_attached_services WHERE product_id = :id"), {"id": product_id})
        await session.execute(
            text(
                """
                UPDATE product_variants
                SET deleted_at = NOW(),
                    status = 'deleted',
                    is_active = FALSE,
                    is_default = FALSE,
                    updated_at = NOW()
                WHERE product_id = :id AND deleted_at IS NULL
                """
            ),
            {"id": product_id},
        )
        await session.execute(
            text("UPDATE products SET status = 'ARCHIVED', deleted_at = NOW(), updated_at = NOW() WHERE id = :id"),
            {"id": product_id},
        )
        await session.commit()
        return {"ok": True, "action": "revision_discarded"}
    await ensure_categories_not_migrating(session, [product_category_row["category_id"], product_category_row["subcategory_id"]])
    usage = (
        await session.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM order_items WHERE product_id = :id) AS order_count,
                    (SELECT COUNT(*) FROM product_reviews WHERE product_id = :id) AS review_count
                """
            ),
            {"id": product_id},
        )
    ).mappings().one()
    if usage["order_count"] == 0 and usage["review_count"] == 0:
        result = await session.execute(text("UPDATE products SET status = 'ARCHIVED', updated_at = NOW() WHERE id = :id"), {"id": product_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm.")
        await session.commit()
        return {"ok": True, "action": "archived"}

    await session.execute(text("UPDATE products SET status = 'INACTIVE', updated_at = NOW() WHERE id = :id"), {"id": product_id})
    await session.commit()
    return {"ok": True, "action": "deactivated"}


@router.delete("/products/{product_id}/variants/{variant_id}", dependencies=[Depends(require_permission("product:delete"))])
async def delete_product_variant(
    product_id: UUID,
    variant_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    variant = (
        await session.execute(
            text(
                """
                SELECT id, is_default, sku
                FROM product_variants
                WHERE id = :variant_id AND product_id = :product_id AND deleted_at IS NULL
                """
            ),
            {"variant_id": variant_id, "product_id": product_id},
        )
    ).mappings().first()
    if not variant:
        raise HTTPException(status_code=404, detail="Không tìm thấy biến thể.")

    active_count = (
        await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM product_variants
                WHERE product_id = :product_id AND deleted_at IS NULL
                """
            ),
            {"product_id": product_id},
        )
    ).scalar_one()

    if active_count <= 1:
        raise HTTPException(
            status_code=400,
            detail="Sản phẩm phải có ít nhất một biến thể.",
            headers={"x-error-code": "CANNOT_DELETE_LAST_VARIANT"}
        )

    await session.execute(
        text(
            """
            UPDATE product_variants
            SET deleted_at = NOW(),
                status = 'deleted',
                is_active = FALSE,
                is_default = FALSE,
                updated_at = NOW()
            WHERE id = :variant_id
            """
        ),
        {"variant_id": variant_id},
    )

    if variant["is_default"]:
        next_variant = (
            await session.execute(
                text(
                    """
                    SELECT id, sku
                    FROM product_variants
                    WHERE product_id = :product_id AND deleted_at IS NULL
                    ORDER BY created_at ASC
                    LIMIT 1
                    """
                ),
                {"product_id": product_id},
            )
        ).mappings().first()
        if next_variant:
            await session.execute(
                text(
                    """
                    UPDATE product_variants
                    SET is_default = TRUE,
                        updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": next_variant["id"]},
            )
            await session.execute(
                text(
                    """
                    UPDATE products
                    SET sku = :sku,
                        updated_at = NOW()
                    WHERE id = :product_id
                    """
                ),
                {"sku": next_variant["sku"], "product_id": product_id},
            )

    await session.commit()
    return {"ok": True}
