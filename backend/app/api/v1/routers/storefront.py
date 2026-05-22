import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.catalog import product_row
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import get_session


router = APIRouter(prefix="/storefront", tags=["Storefront"])


@router.get("/policies")
async def list_storefront_policies(
    code: str | None = None,
    product_id: str | None = None,
    category_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                code,
                title,
                summary,
                content,
                seo_title AS "seoTitle",
                seo_description AS "seoDescription",
                seo_keywords AS "seoKeywords",
                scope_type AS "scopeType",
                COALESCE(product_ids, '[]'::jsonb) AS "productIds",
                COALESCE(category_ids, '[]'::jsonb) AS "categoryIds",
                published_at AS "publishedAt",
                updated_at AS "updatedAt"
            FROM policies
            WHERE is_active = TRUE
              AND (
                status = 'PUBLISHED'
                OR (status = 'SCHEDULED' AND scheduled_at IS NOT NULL AND scheduled_at <= NOW())
              )
              AND (:code IS NULL OR code = :code)
              AND (
                OR scope_type = 'GLOBAL'
                OR (
                  :product_id IS NULL
                  AND :category_id IS NULL
                )
                OR (
                  :product_id IS NOT NULL
                  AND COALESCE(product_ids, '[]'::jsonb) ? :product_id
                )
                OR (
                  :category_id IS NOT NULL
                  AND COALESCE(category_ids, '[]'::jsonb) ? :category_id
                )
              )
            ORDER BY COALESCE(published_at, updated_at) DESC, updated_at DESC
            """
        ),
        {
            "code": code.strip().lower() if code else None,
            "product_id": product_id.strip() if product_id else None,
            "category_id": category_id.strip() if category_id else None,
        },
    )
    return [dict(row._mapping) for row in result]


async def resolve_brand_redirect(session: AsyncSession, slug: str, max_hops: int = 5) -> str | None:
    current = slug
    seen = {slug}
    for _ in range(max_hops):
        next_slug = (
            await session.execute(
                text("SELECT new_slug FROM brand_slug_redirects WHERE old_slug = :slug"),
                {"slug": current},
            )
        ).scalar_one_or_none()
        if not next_slug:
            return current if current != slug else None
        if next_slug in seen:
            raise HTTPException(status_code=409, detail="Brand redirect loop detected.")
        seen.add(str(next_slug))
        current = str(next_slug)
    raise HTTPException(status_code=409, detail="Brand redirect chain is too long.")


@router.get("/brands/{slug}")
async def get_brand_landing(
    slug: str,
    response: Response,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=24, ge=1, le=60),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    brand_result = await session.execute(
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
                seo_title AS "seoTitle",
                seo_description AS "seoDescription",
                cache_version AS "cacheVersion",
                sort_order AS "order"
            FROM brands
            WHERE slug = :slug AND is_active = TRUE
            """
        ),
        {"slug": slug},
    )
    brand = brand_result.mappings().first()
    if not brand:
        redirect = await resolve_brand_redirect(session, slug)
        if redirect:
            response.status_code = status.HTTP_308_PERMANENT_REDIRECT
            response.headers["Location"] = f"/api/v1/storefront/brands/{redirect}"
            return {"redirectTo": redirect}
        raise HTTPException(status_code=404, detail="Brand not found.")

    cache_key = f"storefront:brand:{brand['slug']}:v:{brand['cacheVersion']}:page:{page}:limit:{limit}"
    try:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    total = (
        await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM products p
                WHERE p.status = 'ACTIVE'
                  AND (p.brand_id = CAST(:brand_id AS uuid) OR p.brand = :brand_name)
                """
            ),
            {"brand_id": brand["id"], "brand_name": brand["name"]},
        )
    ).scalar_one()

    product_result = await session.execute(
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
        {"brand_id": brand["id"], "brand_name": brand["name"], "limit": limit, "offset": (page - 1) * limit},
    )
    payload = {
        "brand": dict(brand),
        "products": [product_row(row) for row in product_result],
        "pagination": {"page": page, "limit": limit, "total": total},
    }
    try:
        await redis.setex(cache_key, 30 * 60, json.dumps(payload, ensure_ascii=False, default=str))
    except Exception:
        pass
    return payload
