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
from app.api.v1.routers.admin_product_utils import (
    persisted_sales_config,
    sync_parent_price_from_variants,
    sync_parent_price_if_variants_exist,
    normalized_option_key,
    normalize_product_options,
    extract_product_metadata,
    validate_optimized_media,
    resolve_catalog_labels,
)
from app.api.v1.routers.admin_product_variants import upsert_product_variants, delete_product_variant
from app.infrastructure.database.session import AsyncSessionFactory, get_session

router = APIRouter()
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
MAX_PRODUCT_IMAGE_BYTES = 10 * 1024 * 1024


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
    normalized_status_filter = None if not status_filter or status_filter.lower() == "all" else status_filter
    params = {
        "search": search_text,
        "pattern": f"%{search_text}%",
        "status_filter": normalized_status_filter,
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
                :price, :sale_price, :stock_quantity, :image_url, CAST(:images AS jsonb), :video_url,
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
            "stock_quantity": payload.stock,
            "image_url": payload.imageUrl,
            "images": json.dumps(payload.images),
            "video_url": payload.videoUrl,
            "is_featured": payload.isFeatured,
            "is_flash_sale": payload.isFlashSale,
            "options": json.dumps(clean_options),
        },
    )
    await upsert_product_variants(session, revision_id, payload.variants, payload.name, payload.price, payload.discountPrice, payload.stock)
    await sync_parent_price_if_variants_exist(session, revision_id)
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
                :description, CAST(:specifications AS jsonb), CAST(:seo_metadata AS jsonb), CAST(:sales_config AS jsonb), :price, :sale_price, :stock_quantity, :image_url,
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
            "stock_quantity": payload.stock,
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
    await sync_parent_price_if_variants_exist(session, product_id)
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
    if current["status"] == "MERGED":
        raise HTTPException(status_code=400, detail="Bản chỉnh sửa này đã được áp dụng vào sản phẩm gốc, không thể sửa hoặc khôi phục lại.")
    if current["status"] == "ARCHIVED" and normalize_status(payload.status) == "ACTIVE":
        raise HTTPException(status_code=400, detail="Sản phẩm đã lưu trữ không thể khôi phục trực tiếp. Vui lòng tạo bản nháp mới nếu cần bán lại.")
    if current["status"] == "ACTIVE":
        return await create_product_revision(session, product_id, payload, clean_specs, seo_metadata, sales_config, category, brand)
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
                stock_quantity = :stock_quantity,
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
            "stock_quantity": payload.stock,
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
    await sync_parent_price_if_variants_exist(session, product_id)
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
                LEFT(CONCAT(sku, '-COPY-', CAST(:suffix AS TEXT)), 120),
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
