from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_session
from app.api.v1.routers.catalog_categories import router as catalog_categories_router
from app.api.v1.routers.catalog_products import router as catalog_products_router
from app.api.v1.routers.catalog_search import router as catalog_search_router
from app.api.v1.routers.catalog_utils import product_row

router = APIRouter(prefix="/catalog", tags=["Catalog"])
router.include_router(catalog_categories_router)
router.include_router(catalog_products_router)
router.include_router(catalog_search_router)

@router.get("/brands")
async def list_brands(session: AsyncSession = Depends(get_session)) -> list[dict]:
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

@router.get("/products")
async def list_products(
    q: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=50),
    brand: str | None = Query(default=None, max_length=50),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    flash_sale: bool | None = Query(default=None, alias="flash_sale"),
    featured: bool | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    query_params = {}
    where_clauses = ["p.status = 'ACTIVE'", "p.deleted_at IS NULL"]

    if q and q.strip():
        # Will do python search scoring for keyword q
        pass

    if brand and brand.lower() != "all":
        where_clauses.append("(p.brand = :brand OR b.slug = :brand)")
        query_params["brand"] = brand

    if min_price is not None:
        where_clauses.append("COALESCE(p.sale_price, p.price) >= :min_price")
        query_params["min_price"] = min_price

    if max_price is not None:
        where_clauses.append("COALESCE(p.sale_price, p.price) <= :max_price")
        query_params["max_price"] = max_price

    if featured is not None:
        where_clauses.append("p.is_featured = :featured")
        query_params["featured"] = featured

    where_sql = " AND ".join(where_clauses)
    
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
    
    result = await session.execute(text(sql), query_params)
    rows = result.all()
    
    items = [product_row(row) for row in rows]
    
    from app.api.v1.routers.catalog_utils import product_matches_category, product_search_score, approximate_trend_score, current_price
    
    # Category filter in python
    if category and category.lower() != "all":
        items = [item for item in items if product_matches_category(item, category)]

    # Flash sale filter in python
    if flash_sale is not None:
        items = [item for item in items if item.get("isFlashSale") == flash_sale]

    # Keyword search filter in python
    if q and q.strip():
        scored_items = []
        for item in items:
            score = product_search_score(item, q)
            if score > 0:
                item["_search_score"] = score
                scored_items.append(item)
        items = scored_items
        
    # Sort in python
    if q and q.strip():
        items.sort(key=lambda item: (-item["_search_score"], -approximate_trend_score(item)))
    elif sort == "price_asc":
        items.sort(key=lambda item: current_price(item))
    elif sort == "price_desc":
        items.sort(key=lambda item: current_price(item), reverse=True)
    elif sort == "trending":
        items.sort(key=lambda item: approximate_trend_score(item), reverse=True)
    elif sort == "rating":
        items.sort(key=lambda item: (item.get("rating") or 0.0, item.get("reviewCount") or 0), reverse=True)
    elif sort == "newest":
        items.sort(key=lambda item: item.get("id", ""), reverse=True)
    else:
        # Default sort by approximate trend score
        items.sort(key=lambda item: approximate_trend_score(item), reverse=True)

    return items[offset : offset + limit]
