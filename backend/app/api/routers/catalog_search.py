from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_session
from app.infrastructure.database.repositories import catalog_search_repo
from app.application.ai.search_intent import (
    ProductSearchIntentRequest,
    ProductSearchIntentResponse,
    parse_product_search_intent,
)
from app.api.routers.catalog_utils import (
    ProductAnalyticsEventRequest,
    normalize_search_text,
    request_ip,
    product_row,
    ranking_row,
    build_product_image_collection,
)

router = APIRouter()

def ranking_history_sql_config(period: str) -> dict[str, str]:
    if period == "24h":
        return {
            "start": "date_trunc('hour', NOW()) - INTERVAL '23 hours'",
            "series": "GENERATE_SERIES(date_trunc('hour', NOW()) - INTERVAL '23 hours', date_trunc('hour', NOW()), INTERVAL '1 hour')",
            "bucket": "date_trunc('hour', created_at)",
            "label": "to_char(d.bucket_date, 'YYYY-MM-DD HH24') || chr(58) || '00'",
        }
    if period == "1y":
        return {
            "start": "date_trunc('month', NOW()) - INTERVAL '11 months'",
            "series": "GENERATE_SERIES(date_trunc('month', NOW()) - INTERVAL '11 months', date_trunc('month', NOW()), INTERVAL '1 month')",
            "bucket": "date_trunc('month', created_at)",
            "label": "to_char(d.bucket_date, 'YYYY-MM')",
        }

    history_days = 7 if period == "7d" else 30
    return {
        "start": f"CURRENT_DATE - INTERVAL '{history_days - 1} days'",
        "series": f"CAST(GENERATE_SERIES(CURRENT_DATE - INTERVAL '{history_days - 1} days', CURRENT_DATE, INTERVAL '1 day') AS DATE)",
        "bucket": "CAST(created_at AS DATE)",
        "label": "d.bucket_date::text",
    }

@router.get("/rankings")
async def list_rankings(
    period: str = Query(default="month", max_length=15),
    criteria: str = Query(default="trending", max_length=15),
    category: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    period_lower = period.lower()
    criteria_lower = criteria.lower()

    from app.api.routers.catalog_utils import RANKING_PERIODS, RANKING_ORDER_FIELDS

    days = RANKING_PERIODS.get(period_lower, 30)
    order_field = RANKING_ORDER_FIELDS.get(criteria_lower, "trendScore")
    history_sql = ranking_history_sql_config(period_lower)

    category_filter_sql = ""
    category_id_param = None
    if category and category.lower() != "all":
        try:
            category_id_param = UUID(category)
            category_filter_sql = "AND (p.category_id = :category_id OR p.subcategory_id = :category_id)"
        except ValueError:
            category_filter_sql = "AND (p.category ILIKE :category_pattern OR c.slug = :category_slug OR sc.slug = :category_slug)"

    query_params = {
        "days": days,
        "limit": limit,
    }
    if category_id_param:
        query_params["category_id"] = category_id_param
    elif category and category.lower() != "all":
        query_params["category_pattern"] = f"%{category}%"
        query_params["category_slug"] = category

    sql = f"""
        WITH period_views AS (
            SELECT product_id, COUNT(*) AS view_count
            FROM product_view_events
            WHERE created_at >= NOW() - (:days * INTERVAL '1 day')
            GROUP BY product_id
        ),
        previous_period_views AS (
            SELECT product_id, COUNT(*) AS view_count
            FROM product_view_events
            WHERE created_at >= NOW() - (2 * :days * INTERVAL '1 day')
              AND created_at < NOW() - (:days * INTERVAL '1 day')
            GROUP BY product_id
        ),
        period_searches AS (
            SELECT product_id, COUNT(*) AS search_count
            FROM product_search_events
            WHERE created_at >= NOW() - (:days * INTERVAL '1 day')
              AND product_id IS NOT NULL
            GROUP BY product_id
        ),
        previous_period_searches AS (
            SELECT product_id, COUNT(*) AS search_count
            FROM product_search_events
            WHERE created_at >= NOW() - (2 * :days * INTERVAL '1 day')
              AND created_at < NOW() - (:days * INTERVAL '1 day')
              AND product_id IS NOT NULL
            GROUP BY product_id
        ),
        period_solds AS (
            SELECT oi.product_id, SUM(oi.quantity) AS sold_count, SUM(oi.total_price) AS revenue
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status = 'COMPLETED'
              AND o.created_at >= NOW() - (:days * INTERVAL '1 day')
            GROUP BY oi.product_id
        ),
        previous_period_solds AS (
            SELECT oi.product_id, SUM(oi.quantity) AS sold_count
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status = 'COMPLETED'
              AND o.created_at >= NOW() - (2 * :days * INTERVAL '1 day')
              AND o.created_at < NOW() - (:days * INTERVAL '1 day')
            GROUP BY oi.product_id
        ),
        period_likes AS (
            SELECT product_id, COUNT(*) AS like_count
            FROM user_favorite_events
            WHERE action = 'LIKE' AND created_at >= NOW() - (:days * INTERVAL '1 day')
            GROUP BY product_id
        ),
        previous_period_likes AS (
            SELECT product_id, COUNT(*) AS like_count
            FROM user_favorite_events
            WHERE action = 'LIKE'
              AND created_at >= NOW() - (2 * :days * INTERVAL '1 day')
              AND created_at < NOW() - (:days * INTERVAL '1 day')
            GROUP BY product_id
        ),
        period_reviews AS (
            SELECT product_id, COUNT(*) AS review_count, AVG(rating) AS avg_rating
            FROM product_reviews
            WHERE status = 'PUBLISHED' AND created_at >= NOW() - (:days * INTERVAL '1 day')
            GROUP BY product_id
        ),
        previous_period_reviews AS (
            SELECT product_id, COUNT(*) AS review_count
            FROM product_reviews
            WHERE status = 'PUBLISHED'
              AND created_at >= NOW() - (2 * :days * INTERVAL '1 day')
              AND created_at < NOW() - (:days * INTERVAL '1 day')
            GROUP BY product_id
        ),
        -- 24h stats
        views_24h AS (
            SELECT product_id, COUNT(*) AS view_count
            FROM product_view_events
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY product_id
        ),
        searches_24h AS (
            SELECT product_id, COUNT(*) AS search_count
            FROM product_search_events
            WHERE created_at >= NOW() - INTERVAL '24 hours' AND product_id IS NOT NULL
            GROUP BY product_id
        ),
        solds_24h AS (
            SELECT oi.product_id, SUM(oi.quantity) AS sold_count
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status = 'COMPLETED' AND o.created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY oi.product_id
        ),
        likes_24h AS (
            SELECT product_id, COUNT(*) AS like_count
            FROM user_favorite_events
            WHERE action = 'LIKE' AND created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY product_id
        ),
        reviews_24h AS (
            SELECT product_id, COUNT(*) AS review_count, AVG(rating) AS avg_rating
            FROM product_reviews
            WHERE status = 'PUBLISHED' AND created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY product_id
        ),
        -- 7d stats
        views_7d AS (
            SELECT product_id, COUNT(*) AS view_count
            FROM product_view_events
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY product_id
        ),
        searches_7d AS (
            SELECT product_id, COUNT(*) AS search_count
            FROM product_search_events
            WHERE created_at >= NOW() - INTERVAL '7 days' AND product_id IS NOT NULL
            GROUP BY product_id
        ),
        solds_7d AS (
            SELECT oi.product_id, SUM(oi.quantity) AS sold_count
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status = 'COMPLETED' AND o.created_at >= NOW() - INTERVAL '7 days'
            GROUP BY oi.product_id
        ),
        likes_7d AS (
            SELECT product_id, COUNT(*) AS like_count
            FROM user_favorite_events
            WHERE action = 'LIKE' AND created_at >= NOW() - INTERVAL '7 days'
            GROUP BY product_id
        ),
        reviews_7d AS (
            SELECT product_id, COUNT(*) AS review_count, AVG(rating) AS avg_rating
            FROM product_reviews
            WHERE status = 'PUBLISHED' AND created_at >= NOW() - INTERVAL '7 days'
            GROUP BY product_id
        ),
        -- 30d stats
        views_30d AS (
            SELECT product_id, COUNT(*) AS view_count
            FROM product_view_events
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY product_id
        ),
        searches_30d AS (
            SELECT product_id, COUNT(*) AS search_count
            FROM product_search_events
            WHERE created_at >= NOW() - INTERVAL '30 days' AND product_id IS NOT NULL
            GROUP BY product_id
        ),
        solds_30d AS (
            SELECT oi.product_id, SUM(oi.quantity) AS sold_count
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status = 'COMPLETED' AND o.created_at >= NOW() - INTERVAL '30 days'
            GROUP BY oi.product_id
        ),
        likes_30d AS (
            SELECT product_id, COUNT(*) AS like_count
            FROM user_favorite_events
            WHERE action = 'LIKE' AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY product_id
        ),
        reviews_30d AS (
            SELECT product_id, COUNT(*) AS review_count, AVG(rating) AS avg_rating
            FROM product_reviews
            WHERE status = 'PUBLISHED' AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY product_id
        ),
        -- 1y stats
        views_1y AS (
            SELECT product_id, COUNT(*) AS view_count
            FROM product_view_events
            WHERE created_at >= NOW() - INTERVAL '365 days'
            GROUP BY product_id
        ),
        searches_1y AS (
            SELECT product_id, COUNT(*) AS search_count
            FROM product_search_events
            WHERE created_at >= NOW() - INTERVAL '365 days' AND product_id IS NOT NULL
            GROUP BY product_id
        ),
        solds_1y AS (
            SELECT oi.product_id, SUM(oi.quantity) AS sold_count
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status = 'COMPLETED' AND o.created_at >= NOW() - INTERVAL '365 days'
            GROUP BY oi.product_id
        ),
        likes_1y AS (
            SELECT product_id, COUNT(*) AS like_count
            FROM user_favorite_events
            WHERE action = 'LIKE' AND created_at >= NOW() - INTERVAL '365 days'
            GROUP BY product_id
        ),
        reviews_1y AS (
            SELECT product_id, COUNT(*) AS review_count, AVG(rating) AS avg_rating
            FROM product_reviews
            WHERE status = 'PUBLISHED' AND created_at >= NOW() - INTERVAL '365 days'
            GROUP BY product_id
        ),
        -- Historical metrics
        historical_stats AS (
            SELECT
                p_id,
                jsonb_agg(jsonb_build_object('date', day_date, 'views', views, 'searches', searches, 'sales', sales) ORDER BY bucket_date) AS history
            FROM (
                SELECT
                    p.id AS p_id,
                    d.bucket_date,
                    {history_sql["label"]} AS day_date,
                    COALESCE(v.count, 0) AS views,
                    COALESCE(s.count, 0) AS searches,
                    COALESCE(sl.count, 0) AS sales
                FROM products p
                CROSS JOIN (
                    SELECT {history_sql["series"]} AS bucket_date
                ) d
                LEFT JOIN (
                    SELECT product_id, {history_sql["bucket"]} AS bucket_date, COUNT(*) AS count
                    FROM product_view_events
                    WHERE created_at >= {history_sql["start"]}
                    GROUP BY product_id, {history_sql["bucket"]}
                ) v ON v.product_id = p.id AND v.bucket_date = d.bucket_date
                LEFT JOIN (
                    SELECT product_id, {history_sql["bucket"]} AS bucket_date, COUNT(*) AS count
                    FROM product_search_events
                    WHERE product_id IS NOT NULL AND created_at >= {history_sql["start"]}
                    GROUP BY product_id, {history_sql["bucket"]}
                ) s ON s.product_id = p.id AND s.bucket_date = d.bucket_date
                LEFT JOIN (
                    SELECT oi.product_id, {history_sql["bucket"].replace('created_at', 'o.created_at')} AS bucket_date, SUM(oi.quantity) AS count
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE o.status = 'COMPLETED' AND o.created_at >= {history_sql["start"]}
                    GROUP BY oi.product_id, {history_sql["bucket"].replace('created_at', 'o.created_at')}
                ) sl ON sl.product_id = p.id AND sl.bucket_date = d.bucket_date
                ORDER BY d.bucket_date ASC
            ) daily
            GROUP BY p_id
        )
        SELECT
            p.id::text, p.sku, p.name, p.slug, p.category, p.brand,
            c.slug AS "categorySlug", c.name AS "categoryName",
            COALESCE(c.spec_fields, '[]'::jsonb) || COALESCE(sc.spec_fields, '[]'::jsonb) AS "specFields",
            sc.slug AS "subcategorySlug", sc.name AS "subcategoryName",
            p.description, p.specifications, p.price, p.sale_price AS "discountPrice",
            p.stock_quantity AS "stock", p.status, p.image_url AS "imageUrl",
            p.video_url AS "videoUrl", p.images, p.colors, p.capacities, p.promotions,
            p.badge, COALESCE(review_stats.rating, 0) AS rating,
            COALESCE(review_stats.review_count, 0) AS "reviewCount",
            COALESCE(favorite_counts.favorite_count, 0) AS "favoriteCount",
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
            ) AS variants,
            COALESCE(pv_stats.view_count, 0) AS "viewCount",
            COALESCE(ps_stats.search_count, 0) AS "searchCount",
            COALESCE(pso_stats.sold_count, 0) AS "periodSoldCount",
            COALESCE(pso_stats.revenue, 0.0) AS "periodRevenue",
            COALESCE(pl_stats.like_count, 0) AS "periodLikeCount",
            COALESCE(pr_stats.review_count, 0) AS "periodReviewCount",

            COALESCE(prev_pv.view_count, 0) AS "previousViewCount",
            COALESCE(prev_ps.search_count, 0) AS "previousSearchCount",
            COALESCE(prev_pso.sold_count, 0) AS "previousPeriodSoldCount",
            COALESCE(prev_pl.like_count, 0) AS "previousPeriodLikeCount",
            COALESCE(prev_pr.review_count, 0) AS "previousPeriodReviewCount",

            COALESCE(v24.view_count, 0) AS "view24h",
            COALESCE(s24.search_count, 0) AS "search24h",
            COALESCE(sl24.sold_count, 0) AS "sold24h",
            COALESCE(l24.like_count, 0) AS "like24h",
            COALESCE(r24.review_count, 0) AS "review24h",
            COALESCE(r24.avg_rating, 0.0) AS "rating24h",

            COALESCE(v7.view_count, 0) AS "view7d",
            COALESCE(s7.search_count, 0) AS "search7d",
            COALESCE(sl7.sold_count, 0) AS "sold7d",
            COALESCE(l7.like_count, 0) AS "like7d",
            COALESCE(r7.review_count, 0) AS "review7d",
            COALESCE(r7.avg_rating, 0.0) AS "rating7d",

            COALESCE(v30.view_count, 0) AS "view30d",
            COALESCE(s30.search_count, 0) AS "search30d",
            COALESCE(sl30.sold_count, 0) AS "sold30d",
            COALESCE(l30.like_count, 0) AS "like30d",
            COALESCE(r30.review_count, 0) AS "review30d",
            COALESCE(r30.avg_rating, 0.0) AS "rating30d",

            COALESCE(v1y.view_count, 0) AS "view1y",
            COALESCE(s1y.search_count, 0) AS "search1y",
            COALESCE(sl1y.sold_count, 0) AS "sold1y",
            COALESCE(l1y.like_count, 0) AS "like1y",
            COALESCE(r1y.review_count, 0) AS "review1y",
            COALESCE(r1y.avg_rating, 0.0) AS "rating1y",

            h.history
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
            WHERE is_active = TRUE
            GROUP BY product_id
        ) favorite_counts ON favorite_counts.product_id = p.id
        LEFT JOIN period_views pv_stats ON pv_stats.product_id = p.id
        LEFT JOIN period_searches ps_stats ON ps_stats.product_id = p.id
        LEFT JOIN period_solds pso_stats ON pso_stats.product_id = p.id
        LEFT JOIN period_likes pl_stats ON pl_stats.product_id = p.id
        LEFT JOIN period_reviews pr_stats ON pr_stats.product_id = p.id
        LEFT JOIN previous_period_views prev_pv ON prev_pv.product_id = p.id
        LEFT JOIN previous_period_searches prev_ps ON prev_ps.product_id = p.id
        LEFT JOIN previous_period_solds prev_pso ON prev_pso.product_id = p.id
        LEFT JOIN previous_period_likes prev_pl ON prev_pl.product_id = p.id
        LEFT JOIN previous_period_reviews prev_pr ON prev_pr.product_id = p.id

        LEFT JOIN views_24h v24 ON v24.product_id = p.id
        LEFT JOIN searches_24h s24 ON s24.product_id = p.id
        LEFT JOIN solds_24h sl24 ON sl24.product_id = p.id
        LEFT JOIN likes_24h l24 ON l24.product_id = p.id
        LEFT JOIN reviews_24h r24 ON r24.product_id = p.id

        LEFT JOIN views_7d v7 ON v7.product_id = p.id
        LEFT JOIN searches_7d s7 ON s7.product_id = p.id
        LEFT JOIN solds_7d sl7 ON sl7.product_id = p.id
        LEFT JOIN likes_7d l7 ON l7.product_id = p.id
        LEFT JOIN reviews_7d r7 ON r7.product_id = p.id

        LEFT JOIN views_30d v30 ON v30.product_id = p.id
        LEFT JOIN searches_30d s30 ON s30.product_id = p.id
        LEFT JOIN solds_30d sl30 ON sl30.product_id = p.id
        LEFT JOIN likes_30d l30 ON l30.product_id = p.id
        LEFT JOIN reviews_30d r30 ON r30.product_id = p.id

        LEFT JOIN views_1y v1y ON v1y.product_id = p.id
        LEFT JOIN searches_1y s1y ON s1y.product_id = p.id
        LEFT JOIN solds_1y sl1y ON sl1y.product_id = p.id
        LEFT JOIN likes_1y l1y ON l1y.product_id = p.id
        LEFT JOIN reviews_1y r1y ON r1y.product_id = p.id

        LEFT JOIN historical_stats h ON h.p_id = p.id
        WHERE p.status = 'ACTIVE' AND p.deleted_at IS NULL {category_filter_sql}
        GROUP BY p.id, c.id, sc.id, os.sold_count, review_stats.rating, review_stats.review_count,
            favorite_counts.favorite_count, fs.id, fs.discount_type, fs.discount_value, fs.starts_at, fs.ends_at,
            pv_stats.view_count, ps_stats.search_count, pso_stats.sold_count, pso_stats.revenue, pl_stats.like_count, pr_stats.review_count,
            prev_pv.view_count, prev_ps.search_count, prev_pso.sold_count, prev_pl.like_count, prev_pr.review_count,
            v24.view_count, s24.search_count, sl24.sold_count, l24.like_count, r24.review_count, r24.avg_rating,
            v7.view_count, s7.search_count, sl7.sold_count, l7.like_count, r7.review_count, r7.avg_rating,
            v30.view_count, s30.search_count, sl30.sold_count, l30.like_count, r30.review_count, r30.avg_rating,
            v1y.view_count, s1y.search_count, sl1y.sold_count, l1y.like_count, r1y.review_count, r1y.avg_rating,
            h.history
    """
    rows = await catalog_search_repo.execute_rankings_query(session, sql, query_params)

    items = [ranking_row(row) for row in rows]

    # Sort in python for complex criteria
    if order_field in {"trendScore", "searchCount", "viewCount", "favoriteCount", "periodSoldCount", "rating"}:
        items.sort(key=lambda item: (item.get(order_field) or 0, item.get("soldCount") or 0), reverse=True)

    return items[:limit]

@router.get("/images")
async def list_product_images(
    q: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=50),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> dict:
    from app.api.routers.catalog import list_products
    products = await list_products(
        q=None,
        category=None,
        brand=None,
        min_price=None,
        max_price=None,
        sort=None,
        limit=100,
        offset=0,
        flash_sale=None,
        featured=None,
        session=session,
    )
    collection = build_product_image_collection(products, q, category)
    items = collection["items"]

    total_products = len(items)
    total_images = collection["totalImages"]
    total_pages = max(1, (total_products + limit - 1) // limit)
    start_offset = (page - 1) * limit

    return {
        "items": items[start_offset : start_offset + limit],
        "categories": collection["categories"],
        "totalImages": total_images,
        "totalProducts": total_products,
        "page": page,
        "limit": limit,
        "totalPages": total_pages,
        "hasMore": page < total_pages,
    }

@router.get("/images/resolve/{view_id}")
async def resolve_product_image(
    view_id: str,
    limit: int = Query(default=12, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> dict:
    parts = view_id.rsplit("-", 1)
    if len(parts) == 2:
        try:
            prod_id = UUID(parts[0])
            img_index = int(parts[1])
        except ValueError:
            prod_id = None
            img_index = 0

        if prod_id:
            row = await catalog_search_repo.get_active_product_image_source(session, prod_id)

            if row:
                product = dict(row._mapping)
                all_urls = [product.get("imageUrl")] + list(product.get("images") or [])
                all_urls = [u for u in all_urls if u]

                target_url = all_urls[img_index] if img_index < len(all_urls) else (all_urls[0] if all_urls else None)

                # Fetch related products in the same category
                rel_results = await catalog_search_repo.list_related_products_by_category(
                    session,
                    product_id=prod_id,
                    category=product.get("category"),
                    limit=limit,
                )
                related = [product_row(r) for r in rel_results]

                return {
                    "url": target_url,
                    "productId": str(prod_id),
                    "productName": product.get("name"),
                    "brand": product.get("brand"),
                    "category": product.get("category"),
                    "relatedProducts": related,
                }

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found.")

@router.post("/search-intent", response_model=ProductSearchIntentResponse)
async def parse_search_intent(payload: ProductSearchIntentRequest) -> ProductSearchIntentResponse:
    return await parse_product_search_intent(payload)

@router.post("/search-events", status_code=status.HTTP_201_CREATED)
async def record_product_search(
    payload: ProductAnalyticsEventRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    query = (payload.query or "").strip()
    if not query:
        return {"counted": False}
    normalized_query = normalize_search_text(query)
    product_ids = payload.productIds[:50]
    if not product_ids:
        await catalog_search_repo.insert_product_search_event(
            session,
            query=query,
            normalized_query=normalized_query,
            product_id=None,
            session_id=payload.sessionId,
            ip_address=request_ip(request),
            user_agent=request.headers.get("user-agent"),
            result_count=payload.resultCount or 0,
        )
    else:
        for product_id in product_ids:
            await catalog_search_repo.insert_product_search_event(
                session,
                query=query,
                normalized_query=normalized_query,
                product_id=product_id,
                session_id=payload.sessionId,
                ip_address=request_ip(request),
                user_agent=request.headers.get("user-agent"),
                result_count=payload.resultCount or 0,
            )
    await session.commit()
    return {"counted": True, "productCount": len(product_ids)}
