from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_brand_redirect_slug(session: AsyncSession, slug: str) -> str | None:
    return (
        await session.execute(
            text("SELECT new_slug FROM brand_slug_redirects WHERE old_slug = :slug"),
            {"slug": slug},
        )
    ).scalar_one_or_none()


async def get_active_brand_by_slug(session: AsyncSession, slug: str) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    id::text,
                    code,
                    slug,
                    name,
                    logo_url AS "logoUrl",
                    logo_alt_text AS "logoAltText",
                    landing_title AS "landingTitle",
                    cache_version AS "cacheVersion",
                    sort_order AS "order"
                FROM brands
                WHERE slug = :slug AND is_active = TRUE
                """
            ),
            {"slug": slug},
        )
    ).mappings().first()
    return dict(row) if row else None


async def count_active_products_by_brand(session: AsyncSession, *, brand_id: str, brand_name: str) -> int:
    return int(
        (
            await session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM products p
                    WHERE p.status = 'ACTIVE'
                      AND (p.brand_id = CAST(:brand_id AS uuid) OR p.brand = :brand_name)
                    """
                ),
                {"brand_id": brand_id, "brand_name": brand_name},
            )
        ).scalar_one()
        or 0
    )


async def list_active_products_by_brand(
    session: AsyncSession,
    *,
    brand_id: str,
    brand_name: str,
    limit: int,
    offset: int,
) -> list:
    result = await session.execute(
        text(
            """
            SELECT
                p.id::text,
                p.sku,
                p.name,
                p.slug,
                p.category,
                p.brand,
                c.slug AS "categorySlug",
                c.name AS "categoryName",
                COALESCE(c.spec_fields, '[]'::jsonb) || COALESCE(sc.spec_fields, '[]'::jsonb) AS "specFields",
                sc.slug AS "subcategorySlug",
                sc.name AS "subcategoryName",
                p.description,
                p.specifications,
                p.price,
                p.sale_price AS "discountPrice",
                p.stock_quantity AS "stock",
                p.status,
                p.image_url AS "imageUrl",
                p.video_url AS "videoUrl",
                p.images,
                p.colors,
                p.capacities,
                p.promotions,
                p.badge,
                p.rating,
                COALESCE(p.review_count, 0) AS "reviewCount",
                COALESCE(os.sold_count, 0) AS "soldCount",
                p.is_featured AS "isFeatured",
                p.is_flash_sale AS "isFlashSale",
                '[]'::jsonb AS variants
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN categories sc ON sc.id = p.subcategory_id
            LEFT JOIN (
                SELECT oi.product_id, SUM(oi.quantity) AS sold_count
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.status = 'COMPLETED'
                GROUP BY oi.product_id
            ) os ON os.product_id = p.id
            WHERE p.status = 'ACTIVE'
              AND (p.brand_id = CAST(:brand_id AS uuid) OR p.brand = :brand_name)
            GROUP BY p.id, c.id, sc.id, os.sold_count
            ORDER BY p.is_featured DESC, p.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"brand_id": brand_id, "brand_name": brand_name, "limit": limit, "offset": offset},
    )
    return list(result)
