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
                GREATEST(
                    COALESCE(variant_stock.total_stock, 0),
                    COALESCE(p.stock_quantity, 0)
                ) AS "stockQuantity",
                (
                    p.status IN ('ACTIVE', 'APPROVED')
                    AND p.deleted_at IS NULL
                    AND GREATEST(COALESCE(variant_stock.total_stock, 0), COALESCE(p.stock_quantity, 0)) > 0
                ) AS "isSellable",
                p.category_id::text AS "categoryId",
                p.brand_id::text AS "brandId",
                c.name AS "categoryName",
                b.name AS "brandName"
            FROM products p
            LEFT JOIN (
                SELECT product_id, COALESCE(SUM(stock_quantity), 0) AS total_stock
                FROM product_variants
                WHERE is_active = TRUE
                  AND deleted_at IS NULL
                  AND LOWER(COALESCE(status, 'active')) NOT IN ('deleted', 'archived', 'inactive', 'discontinued')
                GROUP BY product_id
            ) variant_stock ON variant_stock.product_id = p.id
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN categories sc ON sc.id = p.subcategory_id
            LEFT JOIN brands b ON b.id = p.brand_id
            WHERE (CAST(:exclude_id AS UUID) IS NULL OR p.id <> CAST(:exclude_id AS UUID))
              AND p.deleted_at IS NULL
              AND (
                CAST(:category_id AS UUID) IS NULL
                OR EXISTS (
                    SELECT 1
                    FROM categories selected
                    JOIN categories product_category ON product_category.id = COALESCE(p.subcategory_id, p.category_id)
                    WHERE selected.id = CAST(:category_id AS UUID)
                      AND product_category.path <@ selected.path
                )
                OR p.category_id = CAST(:category_id AS UUID)
                OR p.subcategory_id = CAST(:category_id AS UUID)
              )
              AND (CAST(:brand_id AS UUID) IS NULL OR p.brand_id = CAST(:brand_id AS UUID))
              AND (
                :search = ''
                OR LOWER(p.name) LIKE LOWER(:pattern)
                OR LOWER(p.sku) LIKE LOWER(:pattern)
                OR LOWER(p.brand) LIKE LOWER(:pattern)
              )
            ORDER BY p.status IN ('ACTIVE', 'APPROVED') DESC, p.name
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
