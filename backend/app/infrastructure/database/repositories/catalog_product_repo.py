from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_active_product_detail(session: AsyncSession, product_id: str):
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
                COALESCE(p.favorite_count, 0) AS "favoriteCount",
                COALESCE(os.sold_count, 0) AS "soldCount",
                p.is_featured AS "isFeatured",
                p.is_flash_sale AS "isFlashSale",
                fs.id::text AS "flashSaleId",
                fs.discount_type AS "flashSaleDiscountType",
                fs.discount_value AS "flashSaleDiscountValue",
                fs.starts_at AS "flashSaleStartsAt",
                fs.ends_at AS "flashSaleEndsAt",
                p.sales_config AS "salesConfig",
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
                            'flashSaleId', vfs.id::text,
                            'flashSaleDiscountType', vfs.discount_type,
                            'flashSaleDiscountValue', vfs.discount_value,
                            'flashSaleStartsAt', vfs.starts_at,
                            'flashSaleEndsAt', vfs.ends_at,
                            'stockQuantity', pv.stock_quantity,
                            'stockState', CASE WHEN pv.stock_quantity > 0 THEN 'IN_STOCK' ELSE 'OUT_OF_STOCK' END
                        )
                    ) FILTER (WHERE pv.id IS NOT NULL),
                    '[]'::jsonb
                ) AS variants
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN categories sc ON sc.id = p.subcategory_id
            LEFT JOIN product_variants pv ON pv.product_id = p.id AND pv.is_active = TRUE AND pv.deleted_at IS NULL
            LEFT JOIN LATERAL (
                SELECT id, discount_type, discount_value, starts_at, ends_at
                FROM flash_sales
                WHERE product_id = p.id
                  AND variant_id = pv.id
                  AND status = 'ACTIVE'
                  AND (starts_at IS NULL OR starts_at <= NOW())
                  AND (ends_at IS NULL OR ends_at >= NOW())
                ORDER BY updated_at DESC
                LIMIT 1
            ) vfs ON TRUE
            LEFT JOIN LATERAL (
                SELECT id, discount_type, discount_value, starts_at, ends_at
                FROM flash_sales
                WHERE product_id = p.id
                  AND variant_id IS NULL
                  AND status = 'ACTIVE'
                  AND (starts_at IS NULL OR starts_at <= NOW())
                  AND (ends_at IS NULL OR ends_at >= NOW())
                ORDER BY updated_at DESC
                LIMIT 1
            ) fs ON TRUE
            LEFT JOIN (
                SELECT oi.product_id, SUM(oi.quantity) AS sold_count
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.status = 'COMPLETED'
                GROUP BY oi.product_id
            ) os ON os.product_id = p.id
            LEFT JOIN (
                SELECT product_id, ROUND(AVG(rating), 2)::numeric(3, 2) AS rating, COUNT(*) AS review_count
                FROM product_reviews
                WHERE status = 'PUBLISHED'
                GROUP BY product_id
            ) review_stats ON review_stats.product_id = p.id
            LEFT JOIN (
                SELECT product_id, COUNT(*) AS favorite_count
                FROM user_favorites
                GROUP BY product_id
            ) favorite_counts ON favorite_counts.product_id = p.id
            WHERE p.status IN ('ACTIVE', 'DISCONTINUED') AND (p.id::text = :product_id OR p.slug = :product_id)
            GROUP BY p.id, c.id, sc.id, os.sold_count, review_stats.rating, review_stats.review_count,
                favorite_counts.favorite_count, fs.id, fs.discount_type, fs.discount_value, fs.starts_at, fs.ends_at
            """
        ),
        {"product_id": product_id},
    )
    return result.first()


async def list_active_brands(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, code, slug, name, logo_url AS "logoUrl", logo_alt_text AS "logoAltText",
                   landing_title AS "landingTitle", sort_order AS "order", is_active AS "isActive"
            FROM brands
            WHERE is_active = TRUE
            ORDER BY sort_order ASC, name ASC
            """
        )
    )
    return [dict(row) for row in result.mappings().all()]


async def list_active_product_rows(session: AsyncSession, *, where_sql: str, params: dict) -> list:
    sql = f"""
        SELECT
            p.id::text, p.sku, p.name, p.slug, p.category, p.brand,
            c.slug AS "categorySlug", c.name AS "categoryName",
            COALESCE(c.spec_fields, '[]'::jsonb) || COALESCE(sc.spec_fields, '[]'::jsonb) AS "specFields",
            sc.slug AS "subcategorySlug", sc.name AS "subcategoryName",
            p.description, p.specifications, p.price, p.sale_price AS "discountPrice",
            p.stock_quantity AS "stock", p.status, p.image_url AS "imageUrl",
            p.video_url AS "videoUrl", p.images, p.colors, p.capacities, p.promotions,
            p.badge, p.rating, COALESCE(p.review_count, 0) AS "reviewCount",
            COALESCE(p.favorite_count, 0) AS "favoriteCount",
            COALESCE(os.sold_count, 0) AS "soldCount",
            p.is_featured AS "isFeatured", p.is_flash_sale AS "isFlashSale",
            fs.id::text AS "flashSaleId", fs.discount_type AS "flashSaleDiscountType",
            fs.discount_value AS "flashSaleDiscountValue", fs.starts_at AS "flashSaleStartsAt",
            fs.ends_at AS "flashSaleEndsAt", p.sales_config AS "salesConfig",
            COALESCE(
                jsonb_agg(
                    DISTINCT jsonb_build_object(
                        'id', pv.id::text, 'sku', pv.sku, 'colorName', pv.color_name, 'colorCode', pv.color_code,
                        'storage', pv.storage, 'ram', pv.ram, 'configuration', pv.configuration, 'specs', pv.specs,
                        'imageUrl', pv.image_url, 'images', pv.images, 'price', pv.price, 'salePrice', pv.sale_price,
                        'flashSaleId', vfs.id::text, 'flashSaleDiscountType', vfs.discount_type,
                        'flashSaleDiscountValue', vfs.discount_value, 'flashSaleStartsAt', vfs.starts_at,
                        'flashSaleEndsAt', vfs.ends_at,
                        'stockQuantity', pv.stock_quantity, 'stockState', CASE WHEN pv.stock_quantity > 0 THEN 'IN_STOCK' ELSE 'OUT_OF_STOCK' END
                    )
                ) FILTER (WHERE pv.id IS NOT NULL),
                '[]'::jsonb
            ) AS variants
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        LEFT JOIN categories sc ON sc.id = p.subcategory_id
        LEFT JOIN brands b ON b.id = p.brand_id
        LEFT JOIN product_variants pv ON pv.product_id = p.id AND pv.is_active = TRUE AND pv.deleted_at IS NULL
        LEFT JOIN LATERAL (
            SELECT id, discount_type, discount_value, starts_at, ends_at
            FROM flash_sales
            WHERE product_id = p.id
              AND variant_id = pv.id
              AND status = 'ACTIVE'
              AND (starts_at IS NULL OR starts_at <= NOW())
              AND (ends_at IS NULL OR ends_at >= NOW())
            ORDER BY updated_at DESC
            LIMIT 1
        ) vfs ON TRUE
        LEFT JOIN LATERAL (
            SELECT id, discount_type, discount_value, starts_at, ends_at
            FROM flash_sales
            WHERE product_id = p.id
              AND variant_id IS NULL
              AND status = 'ACTIVE'
              AND (starts_at IS NULL OR starts_at <= NOW())
              AND (ends_at IS NULL OR ends_at >= NOW())
            ORDER BY updated_at DESC
            LIMIT 1
        ) fs ON TRUE
        LEFT JOIN (
            SELECT oi.product_id, SUM(oi.quantity) AS sold_count
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status = 'COMPLETED'
            GROUP BY oi.product_id
        ) os ON os.product_id = p.id
        WHERE {where_sql}
        GROUP BY p.id, c.id, sc.id, os.sold_count, fs.id, fs.discount_type, fs.discount_value, fs.starts_at, fs.ends_at
    """
    result = await session.execute(text(sql), params)
    return result.all()


async def list_active_accessories(session: AsyncSession, accessory_ids: list[UUID]) -> dict[str, dict]:
    if not accessory_ids:
        return {}
    result = await session.execute(
        text(
            """
            SELECT
                p.id::text,
                p.sku,
                p.name,
                p.price,
                p.sale_price AS "salePrice",
                p.image_url AS "imageUrl",
                fs.id::text AS "flashSaleId",
                fs.discount_type AS "flashSaleDiscountType",
                fs.discount_value AS "flashSaleDiscountValue",
                fs.starts_at AS "flashSaleStartsAt",
                fs.ends_at AS "flashSaleEndsAt"
            FROM products p
            LEFT JOIN LATERAL (
                SELECT id, discount_type, discount_value, starts_at, ends_at
                FROM flash_sales
                WHERE product_id = p.id
                  AND variant_id IS NULL
                  AND status = 'ACTIVE'
                  AND (starts_at IS NULL OR starts_at <= NOW())
                  AND (ends_at IS NULL OR ends_at >= NOW())
                ORDER BY updated_at DESC
                LIMIT 1
            ) fs ON TRUE
            WHERE p.id IN :ids AND p.status = 'ACTIVE' AND p.deleted_at IS NULL
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": accessory_ids},
    )
    return {row["id"]: dict(row) for row in result.mappings().all()}


async def list_product_attached_services(session: AsyncSession, product_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT s.id::text AS "serviceId",
                   s.code,
                   s.name,
                   s.service_type AS "serviceType",
                   s.attribute_group AS "attributeGroup",
                   s.duration_months AS "durationMonths",
                   s.price_mode AS "priceMode",
                   s.fixed_price AS "fixedPrice",
                   s.percent_value AS "percentValue",
                   s.base_amount AS "baseAmount",
                   s.metadata,
                   pas.override_price AS "overridePrice"
            FROM product_attached_services pas
            JOIN attached_services s ON s.id = pas.service_id
            WHERE pas.product_id = :product_id
              AND s.is_active = TRUE
            ORDER BY s.service_type ASC, s.attribute_group ASC NULLS LAST, s.duration_months ASC, s.name ASC
            """
        ),
        {"product_id": product_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_active_attached_services_by_ids(session: AsyncSession, service_ids: list[UUID]) -> list[dict]:
    if not service_ids:
        return []
    result = await session.execute(
        text(
            """
            WITH requested_services AS (
                SELECT id,
                       CASE
                           WHEN code LIKE 'BHMR-PHONE-%' THEN REPLACE(code, 'BHMR-PHONE-', 'S24-MOBILE-')
                           WHEN code LIKE 'BHMR-LAPTOP-%' THEN REPLACE(code, 'BHMR-LAPTOP-', 'S24-LAPTOP-')
                           WHEN code LIKE 'VIP-1D1-PHONE-%' THEN REPLACE(code, 'VIP-1D1-PHONE-', 'VIP-1D1-MOBILE-')
                           WHEN code = 'RVVN-PHONE-12M' THEN 'RVVN-MOBILE-12M'
                           ELSE code
                       END AS resolved_code
                FROM attached_services
                WHERE id IN :ids
            )
            SELECT s.id::text AS "serviceId",
                   s.code,
                   s.name,
                   s.service_type AS "serviceType",
                   s.attribute_group AS "attributeGroup",
                   s.duration_months AS "durationMonths",
                   s.price_mode AS "priceMode",
                   s.fixed_price AS "fixedPrice",
                   s.percent_value AS "percentValue",
                   s.base_amount AS "baseAmount",
                   s.metadata,
                   NULL::numeric AS "overridePrice"
            FROM attached_services s
            WHERE (s.id IN :ids OR s.code IN (SELECT resolved_code FROM requested_services))
              AND s.is_active = TRUE
            ORDER BY s.service_type ASC, s.attribute_group ASC NULLS LAST, s.duration_months ASC, s.name ASC
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": service_ids},
    )
    return [dict(row) for row in result.mappings().all()]


async def get_active_product_uuid(session: AsyncSession, product_id: str) -> UUID | None:
    return await session.scalar(
        text("SELECT id FROM products WHERE status IN ('ACTIVE', 'DISCONTINUED') AND (id::text = :product_id OR slug = :product_id)"),
        {"product_id": product_id},
    )


async def has_recent_product_view_event(
    session: AsyncSession,
    *,
    product_id: UUID,
    device_id: str | None,
    session_id: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> bool:
    return bool(
        await session.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM product_view_events
                WHERE product_id = :product_id
                  AND COALESCE(device_id, session_id, ip_address, user_agent, '') = COALESCE(:device_id, :session_id, :ip_address, :user_agent, '')
                  AND created_at >= NOW() - INTERVAL '24 hours'
                """
            ),
            {
                "product_id": product_id,
                "device_id": device_id,
                "session_id": session_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
        )
    )


async def insert_product_view_event(
    session: AsyncSession,
    *,
    product_id: UUID,
    session_id: str | None,
    device_id: str | None,
    ip_address: str,
    user_agent: str | None,
    source: str | None,
    duration_seconds: int,
    scroll_depth: float,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_view_events
                (product_id, session_id, device_id, ip_address, user_agent, source, duration_seconds, scroll_depth)
            VALUES
                (:product_id, :session_id, :device_id, :ip_address, :user_agent, :source, :duration_seconds, :scroll_depth)
            """
        ),
        {
            "product_id": product_id,
            "session_id": session_id,
            "device_id": device_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "source": source,
            "duration_seconds": duration_seconds,
            "scroll_depth": scroll_depth,
        },
    )


async def get_user_favorite(session: AsyncSession, *, user_id: UUID, product_id: UUID):
    return (
        await session.execute(
            text(
                """
                SELECT id, is_active
                FROM user_favorites
                WHERE user_id = :user_id AND product_id = :product_id
                """
            ),
            {"user_id": user_id, "product_id": product_id},
        )
    ).first()


async def deactivate_favorite(session: AsyncSession, *, user_id: UUID, product_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE user_favorites
            SET is_active = FALSE, updated_at = NOW()
            WHERE user_id = :user_id AND product_id = :product_id
            """
        ),
        {"user_id": user_id, "product_id": product_id},
    )
    await session.execute(
        text("INSERT INTO user_favorite_events (user_id, product_id, action) VALUES (:user_id, :product_id, 'UNLIKE')"),
        {"user_id": user_id, "product_id": product_id},
    )
    await session.execute(
        text("UPDATE products SET favorite_count = favorite_count - 1 WHERE id = :product_id AND favorite_count > 0"),
        {"product_id": product_id},
    )


async def activate_favorite(session: AsyncSession, *, user_id: UUID, product_id: UUID, exists: bool) -> None:
    if exists:
        await session.execute(
            text(
                """
                UPDATE user_favorites
                SET is_active = TRUE, created_at = NOW(), updated_at = NOW()
                WHERE user_id = :user_id AND product_id = :product_id
                """
            ),
            {"user_id": user_id, "product_id": product_id},
        )
    else:
        await session.execute(
            text("INSERT INTO user_favorites (user_id, product_id) VALUES (:user_id, :product_id)"),
            {"user_id": user_id, "product_id": product_id},
        )
    await session.execute(
        text("INSERT INTO user_favorite_events (user_id, product_id, action) VALUES (:user_id, :product_id, 'LIKE')"),
        {"user_id": user_id, "product_id": product_id},
    )
    await session.execute(text("UPDATE products SET favorite_count = favorite_count + 1 WHERE id = :product_id"), {"product_id": product_id})


async def list_favorites(session: AsyncSession, user_id: UUID):
    result = await session.execute(
        text(
            """
            SELECT
                p.id::text, p.sku, p.name, p.slug, p.category, p.brand,
                c.slug AS "categorySlug", c.name AS "categoryName",
                COALESCE(c.spec_fields, '[]'::jsonb) || COALESCE(sc.spec_fields, '[]'::jsonb) AS "specFields",
                sc.slug AS "subcategorySlug", sc.name AS "subcategoryName",
                p.description, p.specifications, p.price, p.sale_price AS "discountPrice",
                p.stock_quantity AS "stock", p.status, p.image_url AS "imageUrl",
                p.video_url AS "videoUrl", p.images, p.colors, p.capacities, p.promotions,
                p.badge, p.rating, COALESCE(p.review_count, 0) AS "reviewCount",
                0 AS "soldCount", p.is_featured AS "isFeatured", p.is_flash_sale AS "isFlashSale",
                uf.created_at AS "favoritedAt", uf.updated_at AS "favoriteUpdatedAt",
                '[]'::jsonb AS variants
            FROM products p
            JOIN user_favorites uf ON uf.product_id = p.id
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN categories sc ON sc.id = p.subcategory_id
            WHERE uf.user_id = :user_id AND uf.is_active = TRUE AND p.status = 'ACTIVE'
            ORDER BY uf.created_at DESC
            """
        ),
        {"user_id": user_id},
    )
    return list(result)


async def insert_draft_product(
    session: AsyncSession,
    *,
    product_id: UUID,
    sku: str,
    name: str,
    slug: str,
    category: str,
    brand: str,
    description: str,
    price: object,
    sale_price: object,
    image_url: str | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, description, specifications, price,
                sale_price, stock_quantity, image_url, images, colors, capacities, promotions, status
            )
            VALUES (
                :id, :sku, :name, :slug, :category, :brand, :description, '{}'::jsonb, :price,
                :sale_price, 0, :image_url, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, 'DRAFT'
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
            "price": price,
            "sale_price": sale_price,
            "image_url": image_url,
        },
    )
