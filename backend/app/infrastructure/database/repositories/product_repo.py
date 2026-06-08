import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_variant_price_summary(session: AsyncSession, product_id: UUID) -> dict | None:
    result = await session.execute(
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
    row = result.mappings().first()
    return dict(row) if row else None


async def update_parent_price_from_summary(
    session: AsyncSession,
    *,
    product_id: UUID,
    price: object,
    sale_price: object,
    stock_quantity: int,
    is_price_out_of_stock: bool,
) -> None:
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
            "stock_quantity": stock_quantity,
            "is_price_out_of_stock": is_price_out_of_stock,
        },
    )


async def has_active_variants(session: AsyncSession, product_id: UUID) -> bool:
    return bool(
        await session.scalar(
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
    )


async def get_category_name(session: AsyncSession, category_id: UUID) -> str | None:
    result = await session.execute(text("SELECT name FROM categories WHERE id = :id"), {"id": category_id})
    row = result.mappings().first()
    return row["name"] if row else None


async def get_brand_name(session: AsyncSession, brand_id: UUID) -> str | None:
    result = await session.execute(text("SELECT name FROM brands WHERE id = :id"), {"id": brand_id})
    row = result.mappings().first()
    return row["name"] if row else None


async def list_admin_product_rows(
    session: AsyncSession,
    *,
    page: int | None,
    limit: int,
    cursor: str | None,
    search: str,
    status_filter: str | None,
    category_id: UUID | None,
    brand_id: UUID | None,
) -> tuple[list[dict], int | None]:
    search_text = search.strip()
    normalized_status_filter = None if not status_filter or status_filter.lower() == "all" else status_filter
    params = {
        "search": search_text,
        "pattern": f"%{search_text}%",
        "status_filter": normalized_status_filter,
        "category_id": category_id,
        "brand_id": brand_id,
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
                    WHEN p.status = 'DRAFT' THEN 'Nháp thêm'
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
    return [dict(row._mapping) for row in result], total


async def suggest_admin_products(
    session: AsyncSession,
    *,
    search: str,
    limit: int,
    exclude_id: UUID | None,
    category_id: UUID | None,
    brand_id: UUID | None,
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
            "exclude_id": exclude_id,
            "category_id": category_id,
            "brand_id": brand_id,
        },
    )
    return [dict(row._mapping) for row in result]


async def create_product_import_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    source_filename: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_import_jobs (id, source_filename, status)
            VALUES (:id, :source_filename, 'PENDING')
            """
        ),
        {"id": job_id, "source_filename": source_filename},
    )


async def list_product_import_jobs(session: AsyncSession) -> list[dict]:
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


async def create_product_export_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    filters: dict,
) -> None:
    await session.execute(
        text("INSERT INTO product_export_jobs (id, status, filters) VALUES (:id, 'PENDING', CAST(:filters AS jsonb))"),
        {"id": job_id, "filters": json.dumps(filters, ensure_ascii=False)},
    )


async def mark_product_export_processing(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text("UPDATE product_export_jobs SET status = 'PROCESSING', updated_at = NOW() WHERE id = :id"),
        {"id": job_id},
    )


async def list_products_for_export(session: AsyncSession, filters: dict) -> list[dict]:
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
    return [dict(row._mapping) for row in result]


async def mark_product_export_completed(
    session: AsyncSession,
    *,
    job_id: UUID,
    total: int,
    file_path: str,
    download_url: str,
    expires_at: datetime,
) -> None:
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
            "total": total,
            "file_path": file_path,
            "download_url": download_url,
            "expires_at": expires_at,
        },
    )


async def mark_product_export_failed(session: AsyncSession, *, job_id: UUID, error: str) -> None:
    await session.execute(
        text("UPDATE product_export_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
        {"id": job_id, "error": error[:1000]},
    )


async def list_product_export_jobs(session: AsyncSession) -> list[dict]:
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


async def get_product_catalog_kpis(session: AsyncSession) -> dict:
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


async def list_product_audit_logs(session: AsyncSession, product_id: UUID) -> list[dict]:
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


async def delete_product_accessories(session: AsyncSession, product_id: UUID) -> None:
    await session.execute(
        text("DELETE FROM product_accessories WHERE product_id = :product_id"),
        {"product_id": product_id},
    )


async def insert_product_accessory(session: AsyncSession, *, product_id: UUID, accessory_id: UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_accessories (product_id, accessory_product_id)
            VALUES (:product_id, :accessory_id)
            ON CONFLICT DO NOTHING
            """
        ),
        {"product_id": product_id, "accessory_id": accessory_id},
    )


async def delete_product_attached_services(session: AsyncSession, product_id: UUID) -> None:
    await session.execute(
        text("DELETE FROM product_attached_services WHERE product_id = :product_id"),
        {"product_id": product_id},
    )


async def get_active_attached_service_group(session: AsyncSession, service_id: UUID) -> dict | None:
    result = await session.execute(
        text("SELECT service_type, attribute_group FROM attached_services WHERE id = :id AND is_active = TRUE"),
        {"id": service_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def upsert_product_attached_service(session: AsyncSession, *, product_id: UUID, service_id: UUID) -> None:
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


async def list_product_bundle_rows(session: AsyncSession, product_ids: list[UUID]) -> list[dict]:
    result = await session.execute(
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
    return [dict(row._mapping) for row in result]


async def list_product_accessory_rows(session: AsyncSession, product_ids: list[UUID]) -> list[dict]:
    result = await session.execute(
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
    return [dict(row._mapping) for row in result]


async def list_product_attached_service_rows(session: AsyncSession, product_ids: list[UUID]) -> list[dict]:
    result = await session.execute(
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
    return [dict(row._mapping) for row in result]


async def mark_product_import_processing(session: AsyncSession, *, job_id: UUID, total: int) -> None:
    await session.execute(
        text("UPDATE product_import_jobs SET status = 'PROCESSING', total_rows = :total, updated_at = NOW() WHERE id = :id"),
        {"id": job_id, "total": total},
    )


async def insert_imported_product(
    session: AsyncSession,
    *,
    product_id: UUID,
    sku: str,
    name: str,
    slug: str,
    category: str,
    brand: str,
    description: str,
    seo_metadata: dict,
    sales_config: dict,
    price: float,
    sale_price: float | None,
    image_url: str | None,
    status: str,
) -> None:
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
            "sku": sku,
            "name": name,
            "slug": slug,
            "category": category,
            "brand": brand,
            "description": description,
            "seo_metadata": json.dumps(seo_metadata),
            "sales_config": json.dumps(sales_config),
            "price": price,
            "sale_price": sale_price,
            "image_url": image_url,
            "status": status,
        },
    )


async def update_product_import_progress(session: AsyncSession, *, job_id: UUID, imported: int, failed: int) -> None:
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


async def mark_product_import_completed(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text("UPDATE product_import_jobs SET status = 'COMPLETED', updated_at = NOW() WHERE id = :id"),
        {"id": job_id},
    )


async def mark_product_import_failed(session: AsyncSession, *, job_id: UUID, error: str) -> None:
    await session.execute(
        text("UPDATE product_import_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
        {"id": job_id, "error": error[:1000]},
    )


async def insert_product_record(
    session: AsyncSession,
    *,
    product_id: UUID,
    sku: str,
    name: str,
    slug: str,
    category: str,
    brand: str,
    category_id: UUID | None,
    subcategory_id: UUID | None,
    brand_id: UUID | None,
    description: str,
    specifications: dict,
    seo_metadata: dict,
    sales_config: dict,
    price: float,
    sale_price: float | None,
    stock_quantity: int,
    image_url: str | None,
    images: list[str],
    video_url: str | None,
    status: str,
    is_featured: bool,
    is_flash_sale: bool,
    options: list[dict],
    parent_product_id: UUID | None = None,
) -> None:
    revision_columns = ", parent_product_id" if parent_product_id else ""
    revision_values = ", :parent_product_id" if parent_product_id else ""
    await session.execute(
        text(
            f"""
            INSERT INTO products (
                id{revision_columns}, sku, name, slug, category, brand, category_id, subcategory_id, brand_id,
                description, specifications, seo_metadata, sales_config, price, sale_price, stock_quantity, image_url,
                images, video_url, colors, capacities, promotions, status, is_featured, is_flash_sale, options
            )
            VALUES (
                :id{revision_values}, :sku, :name, :slug, :category, :brand, :category_id, :subcategory_id, :brand_id,
                :description, CAST(:specifications AS jsonb), CAST(:seo_metadata AS jsonb), CAST(:sales_config AS jsonb),
                :price, :sale_price, :stock_quantity, :image_url, CAST(:images AS jsonb), :video_url,
                '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, :status, :is_featured, :is_flash_sale,
                CAST(:options AS jsonb)
            )
            """
        ),
        {
            "id": product_id,
            "parent_product_id": parent_product_id,
            "sku": sku,
            "name": name,
            "slug": slug,
            "category": category,
            "brand": brand,
            "category_id": category_id,
            "subcategory_id": subcategory_id,
            "brand_id": brand_id,
            "description": description,
            "specifications": json.dumps(specifications),
            "seo_metadata": json.dumps(seo_metadata),
            "sales_config": json.dumps(sales_config),
            "price": price,
            "sale_price": sale_price,
            "stock_quantity": stock_quantity,
            "image_url": image_url,
            "images": json.dumps(images),
            "video_url": video_url,
            "status": status,
            "is_featured": is_featured,
            "is_flash_sale": is_flash_sale,
            "options": json.dumps(options),
        },
    )


async def get_product_current_for_update(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text("SELECT status, version, updated_at, name, price, sale_price, stock_quantity, category_id, subcategory_id FROM products WHERE id = :id"),
            {"id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def product_visibility_blocker(
    session: AsyncSession,
    *,
    product_id: UUID | None = None,
    category_id: UUID | None = None,
    subcategory_id: UUID | None = None,
    brand_id: UUID | None = None,
) -> str | None:
    row = (
        await session.execute(
            text(
                """
                WITH product_scope AS (
                    SELECT
                        COALESCE(CAST(:category_id AS uuid), p.category_id) AS category_id,
                        COALESCE(CAST(:subcategory_id AS uuid), p.subcategory_id) AS subcategory_id,
                        COALESCE(CAST(:brand_id AS uuid), p.brand_id) AS brand_id
                    FROM (SELECT 1) seed
                    LEFT JOIN products p ON p.id = CAST(:product_id AS uuid)
                )
                SELECT
                    category.name AS category_name,
                    category.status AS category_status,
                    category.is_active AS category_is_active,
                    COALESCE(category.is_deleted, FALSE) AS category_is_deleted,
                    brand.name AS brand_name,
                    brand.is_active AS brand_is_active
                FROM product_scope scope
                LEFT JOIN categories category ON category.id = COALESCE(scope.subcategory_id, scope.category_id)
                LEFT JOIN brands brand ON brand.id = scope.brand_id
                """
            ),
            {
                "product_id": product_id,
                "category_id": category_id,
                "subcategory_id": subcategory_id,
                "brand_id": brand_id,
            },
        )
    ).mappings().first()
    if not row:
        return None
    if row["category_name"] and (
        row["category_status"] != "ACTIVE"
        or row["category_is_active"] is not True
        or row["category_is_deleted"] is True
    ):
        return f"Danh mục {row['category_name']} đang ẩn. Hãy bật danh mục trước khi bật sản phẩm."
    if row["brand_name"] and row["brand_is_active"] is not True:
        return f"Thương hiệu {row['brand_name']} đang ẩn. Hãy bật thương hiệu trước khi bật sản phẩm."
    return None


async def update_product_record(
    session: AsyncSession,
    *,
    product_id: UUID,
    name: str,
    category: str,
    brand: str,
    category_id: UUID | None,
    subcategory_id: UUID | None,
    brand_id: UUID | None,
    description: str,
    specifications: dict,
    seo_metadata: dict,
    sales_config: dict,
    price: float,
    sale_price: float | None,
    stock_quantity: int,
    image_url: str | None,
    images: list[str],
    video_url: str | None,
    options: list[dict],
    status: str,
    is_featured: bool,
    is_flash_sale: bool,
) -> int:
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
            "name": name,
            "category": category,
            "brand": brand,
            "category_id": category_id,
            "subcategory_id": subcategory_id,
            "brand_id": brand_id,
            "description": description,
            "specifications": json.dumps(specifications),
            "seo_metadata": json.dumps(seo_metadata),
            "sales_config": json.dumps(sales_config),
            "price": price,
            "sale_price": sale_price,
            "stock_quantity": stock_quantity,
            "image_url": image_url,
            "images": json.dumps(images),
            "video_url": video_url,
            "options": json.dumps(options),
            "status": status,
            "is_featured": is_featured,
            "is_flash_sale": is_flash_sale,
        },
    )
    return int(result.rowcount or 0)


async def deactivate_product_variants(session: AsyncSession, product_id: UUID) -> None:
    await session.execute(
        text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :product_id"),
        {"product_id": product_id},
    )


async def get_product_source_for_duplicate(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(text("SELECT id, name FROM products WHERE id = :id"), {"id": product_id})
    ).mappings().first()
    return dict(row) if row else None


async def duplicate_product_record(
    session: AsyncSession,
    *,
    new_id: UUID,
    source_id: UUID,
    sku: str,
    slug: str,
) -> bool:
    result = await session.execute(
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
        {"new_id": new_id, "source_id": source_id, "sku": sku, "slug": slug},
    )
    return bool(result.first())


async def duplicate_product_variants(session: AsyncSession, *, new_id: UUID, source_id: UUID, suffix: str) -> None:
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
        {"new_id": new_id, "source_id": source_id, "suffix": suffix},
    )


async def duplicate_product_bundles(session: AsyncSession, *, new_id: UUID, source_id: UUID) -> None:
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
        {"new_id": new_id, "source_id": source_id},
    )


async def duplicate_product_accessories(session: AsyncSession, *, new_id: UUID, source_id: UUID) -> None:
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
        {"new_id": new_id, "source_id": source_id},
    )
