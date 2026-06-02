from uuid import UUID, uuid4

import json
import re
import time
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.search_intent import (
    ProductSearchIntentRequest,
    ProductSearchIntentResponse,
    parse_product_search_intent,
)
from app.api.v1.dependencies import get_current_user_id
from app.infrastructure.database.session import get_session
from app.infrastructure.cache import get_redis


router = APIRouter(prefix="/catalog", tags=["Catalog"])
CATEGORY_CACHE_ROOT_ORDER_KEY = "catalog:categories:roots:active"
CATEGORY_CACHE_ROOT_ORDER_STALE_KEY = "catalog:categories:roots:stale"
REDIS_RECOVERY_COOLDOWN_SECONDS = 30
FAVORITE_TOGGLE_RATE_LIMIT = 5
FAVORITE_TOGGLE_RATE_WINDOW_SECONDS = 10
_redis_unavailable_until = 0.0


def category_branch_cache_key(root_id: str, stale: bool = False) -> str:
    return f"catalog:categories:branch:{root_id}:{'stale' if stale else 'active'}"


def redis_cache_available() -> bool:
    return time.perf_counter() >= _redis_unavailable_until


def mark_redis_unavailable() -> None:
    global _redis_unavailable_until
    _redis_unavailable_until = time.perf_counter() + REDIS_RECOVERY_COOLDOWN_SECONDS


async def enforce_favorite_toggle_rate_limit(
    *,
    redis: Redis,
    user_id: UUID,
    product_id: UUID,
) -> None:
    key = f"rate_limit:catalog:favorite:{user_id}:{product_id}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, FAVORITE_TOGGLE_RATE_WINDOW_SECONDS)
    except RedisError:
        mark_redis_unavailable()
        return

    if count > FAVORITE_TOGGLE_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Bạn thao tác yêu thích quá nhanh. Vui lòng thử lại sau vài giây.",
        )


class CreateProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: float = Field(ge=0)
    discountPrice: float | None = Field(default=None, ge=0)
    stock: int = Field(default=0, ge=0)
    brand: str = Field(default="Khác", max_length=100)
    category: str = Field(default="ACCESSORY", max_length=50)
    imageUrl: str | None = None
    description: str | None = None


class ProductAnalyticsEventRequest(BaseModel):
    sessionId: str | None = Field(default=None, max_length=120)
    deviceId: str | None = Field(default=None, max_length=160)
    source: str | None = Field(default=None, max_length=80)
    query: str | None = Field(default=None, max_length=255)
    resultCount: int | None = Field(default=None, ge=0)
    productIds: list[UUID] = Field(default_factory=list, max_length=50)
    activeSeconds: int = Field(default=0, ge=0, le=60)
    scrollDepth: float = Field(default=0, ge=0, le=1)
    clientTimestamp: int | None = Field(default=None, ge=0)


PRODUCT_VIEW_VALID_SECONDS = 30
PRODUCT_VIEW_VALID_SCROLL_DEPTH = 0.5
PRODUCT_VIEW_DEDUPE_SECONDS = 24 * 60 * 60
PRODUCT_VIEW_STATE_TTL_SECONDS = 60 * 60


def request_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


def product_view_identity(payload: ProductAnalyticsEventRequest, request: Request) -> str:
    user_agent = request.headers.get("user-agent") or "unknown"
    ip_address = request_ip(request)
    stable_client_id = payload.deviceId or payload.sessionId or ""
    if stable_client_id:
        return normalize_search_text(f"{stable_client_id} {user_agent}")[:180]
    return normalize_search_text(f"{ip_address} {user_agent}")[:180]


async def insert_valid_product_view(
    *,
    session: AsyncSession,
    product_id: UUID,
    payload: ProductAnalyticsEventRequest,
    request: Request,
    accumulated_seconds: int,
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
            "session_id": payload.sessionId,
            "device_id": payload.deviceId,
            "ip_address": request_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "source": payload.source,
            "duration_seconds": accumulated_seconds,
            "scroll_depth": payload.scrollDepth,
        },
    )
    await session.commit()


def product_row(row) -> dict:
    item = dict(row._mapping)
    stock = item.get("stock") or 0
    stock_state = "IN_STOCK" if int(stock) > 0 else "OUT_OF_STOCK"
    status_value = item.get("status") or "ACTIVE"
    display_status = "Hết hàng" if status_value == "ACTIVE" and stock_state == "OUT_OF_STOCK" else {
        "DRAFT": "Nháp",
        "PENDING": "Chờ duyệt",
        "ACTIVE": "Đang bán",
        "INACTIVE": "Tạm ẩn",
        "ARCHIVED": "Lưu trữ",
    }.get(status_value, status_value)
    return {
        "id": item["id"],
        "sku": item.get("sku"),
        "name": item.get("name"),
        "slug": item.get("slug"),
        "category": item.get("categoryName") or item.get("category") or "",
        "categoryId": str(item.get("categoryId")) if item.get("categoryId") is not None else None,
        "categoryParentId": str(item.get("categoryParentId")) if item.get("categoryParentId") is not None else None,
        "categorySlug": item.get("categorySlug"),
        "subcategoryId": str(item.get("subcategoryId")) if item.get("subcategoryId") is not None else None,
        "subcategoryParentId": str(item.get("subcategoryParentId")) if item.get("subcategoryParentId") is not None else None,
        "subcategorySlug": item.get("subcategorySlug"),
        "specFields": item.get("specFields") or [],
        "brand": item.get("brand"),
        "description": item.get("description"),
        "specs": item.get("specifications") or {},
        "specifications": item.get("specifications") or {},
        "price": float(item.get("price") or 0),
        "discountPrice": float(item["discountPrice"]) if item.get("discountPrice") is not None else None,
        "salePrice": float(item["discountPrice"]) if item.get("discountPrice") is not None else None,
        "stock": stock,
        "stockQuantity": stock,
        "stockState": stock_state,
        "displayStatus": display_status,
        "imageUrl": item.get("imageUrl"),
        "videoUrl": item.get("videoUrl"),
        "images": item.get("images") or [],
        "colors": item.get("colors") or [],
        "capacities": item.get("capacities") or [],
        "promotions": item.get("promotions") or [],
        "badge": item.get("badge"),
        "rating": float(item["rating"]) if item.get("rating") is not None else None,
        "reviewCount": item.get("reviewCount") or 0,
        "favoriteCount": item.get("favoriteCount") or 0,
        "soldCount": item.get("soldCount") or 0,
        "isActive": True,
        "isFeatured": item.get("isFeatured"),
        "isFlashSale": item.get("isFlashSale"),
        "status": status_value,
        "salesConfig": item.get("salesConfig") or {},
        "options": item.get("options") or [],
        "variants": item.get("variants") or [],
    }


RANKING_PERIODS = {
    "24h": 1,
    "7d": 7,
    "30d": 30,
    "1y": 365,
    "month": 30,
    "quarter": 90,
    "year": 365,
}

RANKING_ORDER_FIELDS = {
    "trending": "trendScore",
    "search": "searchCount",
    "view": "viewCount",
    "like": "favoriteCount",
    "sold": "periodSoldCount",
    "rating": "rating",
}


def calc_trend_score(view: int, search: int, sold: int, favorite: int, review: int) -> float:
    if view + search + sold == 0:
        return 0.0
    return round(view * 0.35 + search * 0.25 + sold * 0.25 + favorite * 0.1 + review * 0.05, 2)


def ranking_row(row) -> dict:
    item = product_row(row)
    row_dict = dict(row._mapping)
    
    favorite_count = int(row_dict.get("favoriteCount") or item.get("favoriteCount") or 0)
    review_count = int(row_dict.get("reviewCount") or item.get("reviewCount") or 0)
    period_like_count = int(row_dict.get("periodLikeCount") or 0)
    previous_period_like_count = int(row_dict.get("previousPeriodLikeCount") or 0)
    period_review_count = int(row_dict.get("periodReviewCount") or 0)
    previous_period_review_count = int(row_dict.get("previousPeriodReviewCount") or 0)
    
    period_sold = int(row_dict.get("periodSoldCount") or 0)
    period_revenue = float(row_dict.get("periodRevenue") or 0)
    search_count = int(row_dict.get("searchCount") or 0)
    view_count = int(row_dict.get("viewCount") or 0)
    
    previous_search_count = int(row_dict.get("previousSearchCount") or 0)
    previous_view_count = int(row_dict.get("previousViewCount") or 0)
    previous_period_sold = int(row_dict.get("previousPeriodSoldCount") or 0)
    
    view_24h = int(row_dict.get("view24h") or 0)
    view_7d = int(row_dict.get("view7d") or 0)
    view_30d = int(row_dict.get("view30d") or 0)
    view_1y = int(row_dict.get("view1y") or 0)
    
    search_24h = int(row_dict.get("search24h") or 0)
    search_7d = int(row_dict.get("search7d") or 0)
    search_30d = int(row_dict.get("search30d") or 0)
    search_1y = int(row_dict.get("search1y") or 0)
    
    sold_24h = int(row_dict.get("sold24h") or 0)
    sold_7d = int(row_dict.get("sold7d") or 0)
    sold_30d = int(row_dict.get("sold30d") or 0)
    sold_1y = int(row_dict.get("sold1y") or 0)

    like_24h = int(row_dict.get("like24h") or 0)
    like_7d = int(row_dict.get("like7d") or 0)
    like_30d = int(row_dict.get("like30d") or 0)
    like_1y = int(row_dict.get("like1y") or 0)

    review_24h = int(row_dict.get("review24h") or 0)
    review_7d = int(row_dict.get("review7d") or 0)
    review_30d = int(row_dict.get("review30d") or 0)
    review_1y = int(row_dict.get("review1y") or 0)

    rating_24h = float(row_dict.get("rating24h") or 0.0)
    rating_7d = float(row_dict.get("rating7d") or 0.0)
    rating_30d = float(row_dict.get("rating30d") or 0.0)
    rating_1y = float(row_dict.get("rating1y") or 0.0)
    
    trend_score = calc_trend_score(
        view_count, search_count, period_sold, period_like_count, period_review_count
    )
    previous_trend_score = calc_trend_score(
        previous_view_count,
        previous_search_count,
        previous_period_sold,
        previous_period_like_count,
        previous_period_review_count,
    )
    
    score_24h = calc_trend_score(view_24h, search_24h, sold_24h, like_24h, review_24h)
    score_7d = calc_trend_score(view_7d, search_7d, sold_7d, like_7d, review_7d)
    score_30d = calc_trend_score(view_30d, search_30d, sold_30d, like_30d, review_30d)
    score_1y = calc_trend_score(view_1y, search_1y, sold_1y, like_1y, review_1y)

    item["periodSoldCount"] = period_sold
    item["periodRevenue"] = period_revenue
    item["searchCount"] = search_count
    item["viewCount"] = view_count
    item["previousSearchCount"] = previous_search_count
    item["previousViewCount"] = previous_view_count
    item["previousPeriodSoldCount"] = previous_period_sold
    item["periodLikeCount"] = period_like_count
    item["previousPeriodLikeCount"] = previous_period_like_count
    item["periodReviewCount"] = period_review_count
    item["previousPeriodReviewCount"] = previous_period_review_count
    item["likeCount"] = favorite_count
    item["trendScore"] = trend_score
    item["previousTrendScore"] = previous_trend_score
    
    item["view24h"] = view_24h
    item["view7d"] = view_7d
    item["view30d"] = view_30d
    item["view1y"] = view_1y
    item["search24h"] = search_24h
    item["search7d"] = search_7d
    item["search30d"] = search_30d
    item["search1y"] = search_1y
    item["sold24h"] = sold_24h
    item["sold7d"] = sold_7d
    item["sold30d"] = sold_30d
    item["sold1y"] = sold_1y
    
    item["like24h"] = like_24h
    item["like7d"] = like_7d
    item["like30d"] = like_30d
    item["like1y"] = like_1y

    item["review24h"] = review_24h
    item["review7d"] = review_7d
    item["review30d"] = review_30d
    item["review1y"] = review_1y

    item["rating24h"] = rating_24h
    item["rating7d"] = rating_7d
    item["rating30d"] = rating_30d
    item["rating1y"] = rating_1y

    item["score24h"] = score_24h
    item["score7d"] = score_7d
    item["score30d"] = score_30d
    item["score1y"] = score_1y
    
    item["history"] = row_dict.get("history") or []
    return item


def normalize_search_text(value: object) -> str:
    raw = unicodedata.normalize("NFD", str(value or "").lower())
    raw = "".join(char for char in raw if unicodedata.category(char) != "Mn")
    raw = raw.replace("đ", "d")
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    return raw.strip()


def normalize_category_key(value: object) -> str:
    return normalize_search_text(value).replace(" ", "-")


def product_matches_category(product: dict, category: str | None) -> bool:
    if not category or category == "all":
        return True
    raw_category = str(category)
    normalized_category = normalize_category_key(raw_category)
    category_ids = {
        str(product.get("categoryId") or ""),
        str(product.get("categoryParentId") or ""),
        str(product.get("subcategoryId") or ""),
        str(product.get("subcategoryParentId") or ""),
    }
    if raw_category in category_ids:
        return True
    category_keys = {
        normalize_category_key(product.get("category")),
        normalize_category_key(product.get("categorySlug")),
        normalize_category_key(product.get("subcategorySlug")),
    }
    return normalized_category in category_keys


def term_score(term: str, haystack: str) -> int:
    if not term:
        return 0
    if term in haystack:
        return 18
    compact_haystack = haystack.replace(" ", "")
    compact_term = term.replace(" ", "")
    if compact_term and compact_term in compact_haystack:
        return 14
    return 0


def product_search_score(product: dict, keyword: str) -> int:
    normalized_keyword = normalize_search_text(keyword)
    if not normalized_keyword:
        return 0
    haystack = normalize_search_text(
        " ".join(
            str(part or "")
            for part in [
                product.get("name"),
                product.get("brand"),
                product.get("category"),
                product.get("categorySlug"),
                product.get("subcategorySlug"),
                product.get("description"),
                product.get("sku"),
                json.dumps(product.get("specifications") or {}, ensure_ascii=False),
            ]
        )
    )
    parts = [term for term in normalized_keyword.split(" ") if len(term) > 1]
    if not parts:
        return 0
    score = sum(term_score(term, haystack) for term in parts)
    if normalized_keyword and normalized_keyword in haystack:
        score += 30
    return score


def current_price(product: dict) -> float:
    discount_price = product.get("discountPrice")
    return float(discount_price if discount_price is not None else product.get("price") or 0)


def approximate_trend_score(product: dict) -> float:
    sold_count = float(product.get("soldCount") or 0)
    favorite_count = float(product.get("favoriteCount") or 0)
    review_count = float(product.get("reviewCount") or 0)
    rating = float(product.get("rating") or 0)
    return round(sold_count * 0.55 + favorite_count * 0.2 + review_count * 0.15 + rating * 5, 2)


def is_real_product_image_url(url: object) -> bool:
    value = str(url or "").strip()
    if not value:
        return False
    lower_value = value.lower()
    if "placehold.co" in lower_value or "placeholder" in lower_value:
        return False
    return True


def build_product_image_collection(products: list[dict], q: str | None = None, category: str | None = None) -> dict:
    normalized_keyword = normalize_search_text(q) if q else ""
    normalized_category = normalize_category_key(category) if category and category != "all" else ""
    categories_map: dict[str, dict] = {}
    items: list[dict] = []
    total_images = 0

    for product in products:
        base_urls = [url for url in list(product.get("images") or []) if is_real_product_image_url(url)]
        if not base_urls and is_real_product_image_url(product.get("imageUrl")):
            base_urls = [product["imageUrl"]]
        variant_urls = [
            variant.get("imageUrl")
            for variant in (product.get("variants") or [])
            if is_real_product_image_url(variant.get("imageUrl"))
        ]
        all_urls = list(dict.fromkeys([*base_urls, *variant_urls]))
        if not all_urls:
            continue

        category_name = product.get("category") or ""
        category_key = normalize_category_key(category_name)
        if normalized_category and normalized_category != category_key:
            continue

        haystack = normalize_search_text(f"{product.get('name', '')} {product.get('brand', '')} {category_name}")
        if normalized_keyword and normalized_keyword not in haystack:
            continue

        total_images += len(all_urls)
        if category_name:
            existing = categories_map.get(category_key)
            if existing:
                existing["count"] += 1
            else:
                categories_map[category_key] = {"label": category_name, "count": 1}

        items.append(
            {
                "id": product["id"],
                "productId": product["id"],
                "productName": product.get("name"),
                "brand": product.get("brand"),
                "category": category_name,
                "mainUrl": all_urls[0],
                "imageCount": len(all_urls),
                "trendScore": approximate_trend_score(product),
                "product": product,
                "images": [
                    {
                        "id": f"{product['id']}-{index}",
                        "url": url,
                        "productId": product["id"],
                        "productName": product.get("name"),
                        "brand": product.get("brand"),
                        "category": category_name,
                        "product": product,
                    }
                    for index, url in enumerate(all_urls)
                ],
            }
        )

    items.sort(
        key=lambda item: (
            item.get("trendScore") or 0,
            item.get("product", {}).get("soldCount") or 0,
            item.get("product", {}).get("favoriteCount") or 0,
            item.get("product", {}).get("rating") or 0,
        ),
        reverse=True,
    )
    return {
        "items": items,
        "categories": sorted(categories_map.values(), key=lambda item: (-item["count"], item["label"])),
        "totalImages": total_images,
    }


async def read_category_tree_from_branch_cache(redis: Redis, stale: bool = False) -> list[dict] | None:
    root_ids_payload = await redis.get(CATEGORY_CACHE_ROOT_ORDER_STALE_KEY if stale else CATEGORY_CACHE_ROOT_ORDER_KEY)
    if not root_ids_payload:
        return None
    root_ids = json.loads(root_ids_payload)
    branches: list[dict] = []
    for root_id in root_ids:
        cached_branch = await redis.get(category_branch_cache_key(str(root_id), stale=stale))
        if not cached_branch:
            return None
        branches.append(json.loads(cached_branch))
    return branches


@router.get("/categories")
async def list_categories(session: AsyncSession = Depends(get_session), redis: Redis = Depends(get_redis)) -> list[dict]:
    started = time.perf_counter()
    if redis_cache_available():
        try:
            cached_tree = await read_category_tree_from_branch_cache(redis)
            if not cached_tree:
                cached_tree = await read_category_tree_from_branch_cache(redis, stale=True)
            if not cached_tree:
                active_key = await redis.get("catalog:categories:tree:active")
                cached = await redis.get(active_key) if active_key and active_key != "catalog:categories:tree:branch-cache" else None
                if not cached:
                    cached = await redis.get("catalog:categories:tree:stale")
                cached_tree = json.loads(cached) if cached else None
            if cached_tree:
                await redis.incr("metrics:catalog_categories:cache_hit")
                await redis.lpush("metrics:catalog_categories:latency_ms", int((time.perf_counter() - started) * 1000))
                await redis.ltrim("metrics:catalog_categories:latency_ms", 0, 499)
                return cached_tree
            await redis.incr("metrics:catalog_categories:cache_miss")
        except Exception:
            mark_redis_unavailable()
    result = await session.execute(
        text(
            """
            SELECT
                c.id::text,
                c.parent_id::text AS "parentId",
                c.code,
                c.slug,
                c.name,
                c.icon,
                c.icon_url AS "iconUrl",
                c.banner_url AS "bannerUrl",
                c.seo_title AS "seoTitle",
                c.seo_description AS "seoDescription",
                c.seo_keywords AS "seoKeywords",
                COALESCE(c.spec_fields, '[]'::jsonb) AS "specFields",
                c.filter_config AS "filterConfig",
                c.sort_order AS "order",
                COALESCE(
                    jsonb_agg(
                        DISTINCT jsonb_build_object(
                            'id', child.id::text,
                            'code', child.code,
                            'slug', child.slug,
                            'name', child.name,
                            'sortOrder', child.sort_order
                        )
                    ) FILTER (WHERE child.id IS NOT NULL AND COALESCE(child.is_deleted, FALSE) = FALSE AND child.status = 'ACTIVE'),
                    '[]'::jsonb
                ) AS children
            FROM categories c
            LEFT JOIN categories child ON child.parent_id = c.id
            WHERE c.parent_id IS NULL
              AND c.is_active = TRUE
              AND c.status = 'ACTIVE'
              AND COALESCE(c.is_deleted, FALSE) = FALSE
            GROUP BY c.id
            ORDER BY c.sort_order, c.name
            """
        )
    )
    categories = [dict(row._mapping) for row in result]
    if redis_cache_available():
        try:
            payload = json.dumps(categories, ensure_ascii=False, default=str)
            versioned_key = "catalog:categories:tree:fallback"
            await redis.setex(versioned_key, 30 * 60, payload)
            await redis.set("catalog:categories:tree:active", versioned_key)
            await redis.setex("catalog:categories:tree:stale", 24 * 60 * 60, payload)
            await redis.lpush("metrics:catalog_categories:latency_ms", int((time.perf_counter() - started) * 1000))
            await redis.ltrim("metrics:catalog_categories:latency_ms", 0, 499)
        except Exception:
            mark_redis_unavailable()
    return categories


@router.get("/redirects/{old_slug}")
async def get_category_redirect(old_slug: str, session: AsyncSession = Depends(get_session)) -> dict:
    row = (
        await session.execute(
            text(
                """
                SELECT source_path AS "sourcePath", target_path AS "targetPath", status_code AS "statusCode"
                FROM url_redirects
                WHERE source_path = :source_path
                  AND entity_type = 'category'
                """
            ),
            {"source_path": f"/category/{old_slug}"},
        )
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Redirect not found.")
    return dict(row)


@router.get("/brands")
async def list_brands(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                b.id::text,
                b.code,
                b.slug,
                b.name,
                b.logo_url AS "logoUrl",
                b.logo_alt_text AS "logoAltText",
                b.landing_title AS "landingTitle",
                b.seo_title AS "seoTitle",
                b.seo_description AS "seoDescription",
                COALESCE(
                    jsonb_agg(
                        DISTINCT jsonb_build_object(
                            'id', c.id::text,
                            'code', c.code,
                            'slug', c.slug,
                            'name', c.name
                        )
                    ) FILTER (WHERE c.id IS NOT NULL),
                    '[]'::jsonb
                ) AS categories
            FROM brands b
            LEFT JOIN brand_categories bc ON bc.brand_id = b.id
            LEFT JOIN categories c ON c.id = bc.category_id
            WHERE b.is_active = TRUE
            GROUP BY b.id
            ORDER BY b.sort_order, b.name
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.get("/products")
async def list_products(
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort: str = Query(default="default"),
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    flash_sale: bool | None = Query(default=None),
    featured: bool | None = Query(default=None),
) -> list[dict]:
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
                c.id::text AS "categoryId",
                c.parent_id::text AS "categoryParentId",
                c.slug AS "categorySlug",
                c.name AS "categoryName",
                COALESCE(c.spec_fields, '[]'::jsonb) || COALESCE(sc.spec_fields, '[]'::jsonb) AS "specFields",
                sc.id::text AS "subcategoryId",
                sc.parent_id::text AS "subcategoryParentId",
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
                p.options,
                p.promotions,
                p.badge,
                p.rating,
                COALESCE(p.review_count, 0) AS "reviewCount",
                COALESCE(p.favorite_count, 0) AS "favoriteCount",
                COALESCE(os.sold_count, 0) AS "soldCount",
                p.is_featured AS "isFeatured",
                p.is_flash_sale AS "isFlashSale",
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
                            'attributes', pv.attributes,
                            'stockState', CASE WHEN pv.stock_quantity > 0 THEN 'IN_STOCK' ELSE 'OUT_OF_STOCK' END
                        )
                    ) FILTER (WHERE pv.id IS NOT NULL),
                    '[]'::jsonb
                ) AS variants
            FROM products p
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN categories sc ON sc.id = p.subcategory_id
            LEFT JOIN product_variants pv ON pv.product_id = p.id AND pv.is_active = TRUE AND pv.deleted_at IS NULL
            LEFT JOIN (
                SELECT oi.product_id, SUM(oi.quantity) AS sold_count
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.status = 'COMPLETED'
                GROUP BY oi.product_id
            ) os ON os.product_id = p.id
            WHERE p.status = 'ACTIVE'
            GROUP BY p.id, c.id, sc.id, os.sold_count
            ORDER BY p.is_featured DESC, p.created_at DESC
            """
        )
    )
    items = [product_row(row) for row in result]

    normalized_category = normalize_category_key(category) if category and category != "all" else ""
    normalized_brand = normalize_search_text(brand) if brand and brand != "all" else ""
    keyword = (q or "").strip()

    filtered: list[dict] = []
    for item in items:
        if not product_matches_category(item, category):
            continue

        if normalized_brand and normalize_search_text(item.get("brand")) != normalized_brand:
            continue

        if flash_sale is not None and bool(item.get("isFlashSale")) is not flash_sale:
            continue

        if featured is not None and bool(item.get("isFeatured")) is not featured:
            continue

        price = current_price(item)
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price >= max_price:
            continue

        if keyword:
            score = product_search_score(item, keyword)
            if score <= 0:
                continue
            item["_searchScore"] = score

        filtered.append(item)

    if sort == "price-asc":
        filtered.sort(key=current_price)
    elif sort == "price-desc":
        filtered.sort(key=current_price, reverse=True)
    elif sort == "name-asc":
        filtered.sort(key=lambda item: str(item.get("name") or "").lower())
    elif keyword:
        filtered.sort(key=lambda item: (item.get("_searchScore", 0), item.get("rating") or 0, item.get("soldCount") or 0), reverse=True)

    if offset:
        filtered = filtered[offset:]
    if limit is not None:
        filtered = filtered[:limit]

    for item in filtered:
        item.pop("_searchScore", None)
    return filtered


@router.get("/rankings")
async def list_rankings(
    period: str = "month",
    criteria: str = Query(default="sold"),
    category: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    period_days = RANKING_PERIODS.get(period)
    if period_days is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ranking period.")
    if criteria not in RANKING_ORDER_FIELDS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ranking criteria.")
    result = await session.execute(
        text(
            """
            WITH bounds AS (
                SELECT
                    NOW() - (CAST(:period_days AS integer) * INTERVAL '1 day') AS period_start,
                    NOW() - (CAST(:period_days AS integer) * INTERVAL '2 day') AS previous_start,
                    CASE
                        WHEN CAST(:period_days AS integer) <= 1 THEN INTERVAL '1 hour'
                        WHEN CAST(:period_days AS integer) <= 30 THEN INTERVAL '1 day'
                        ELSE INTERVAL '1 month'
                    END AS bucket_size,
                    CASE
                        WHEN CAST(:period_days AS integer) <= 1 THEN date_trunc('hour', NOW()) - INTERVAL '23 hours'
                        WHEN CAST(:period_days AS integer) = 7 THEN date_trunc('day', NOW()) - INTERVAL '6 days'
                        WHEN CAST(:period_days AS integer) <= 30 THEN date_trunc('day', NOW()) - INTERVAL '29 days'
                        ELSE date_trunc('month', NOW()) - INTERVAL '11 months'
                    END AS chart_start,
                    CASE
                        WHEN CAST(:period_days AS integer) <= 1 THEN date_trunc('hour', NOW())
                        WHEN CAST(:period_days AS integer) <= 30 THEN date_trunc('day', NOW())
                        ELSE date_trunc('month', NOW())
                    END AS chart_end
            ),
            view_counts AS (
                SELECT product_id, COUNT(*) AS view_count
                FROM product_view_events, bounds
                WHERE created_at >= bounds.period_start
                GROUP BY product_id
            ),
            previous_view_counts AS (
                SELECT product_id, COUNT(*) AS view_count
                FROM product_view_events, bounds
                WHERE created_at >= bounds.previous_start
                  AND created_at < bounds.period_start
                GROUP BY product_id
            ),
            search_counts AS (
                SELECT product_id, COUNT(*) AS search_count
                FROM product_search_events, bounds
                WHERE created_at >= bounds.period_start
                  AND product_id IS NOT NULL
                GROUP BY product_id
            ),
            previous_search_counts AS (
                SELECT product_id, COUNT(*) AS search_count
                FROM product_search_events, bounds
                WHERE created_at >= bounds.previous_start
                  AND created_at < bounds.period_start
                  AND product_id IS NOT NULL
                GROUP BY product_id
            ),
            all_favorite_counts AS (
                SELECT product_id, COUNT(*) AS favorite_count
                FROM user_favorites
                WHERE is_active = TRUE
                GROUP BY product_id
            ),
            all_review_stats AS (
                SELECT product_id, COUNT(*) AS review_count, ROUND(AVG(rating)::numeric, 2) AS rating
                FROM product_reviews
                WHERE status = 'PUBLISHED'
                GROUP BY product_id
            ),
            period_like_counts AS (
                SELECT
                    product_id,
                    SUM(CASE WHEN action = 'LIKE' THEN 1 ELSE -1 END) AS like_count
                FROM user_favorite_events, bounds
                WHERE created_at >= bounds.period_start
                GROUP BY product_id
            ),
            previous_like_counts AS (
                SELECT
                    product_id,
                    SUM(CASE WHEN action = 'LIKE' THEN 1 ELSE -1 END) AS like_count
                FROM user_favorite_events, bounds
                WHERE created_at >= bounds.previous_start
                  AND created_at < bounds.period_start
                GROUP BY product_id
            ),
            period_review_stats AS (
                SELECT product_id, COUNT(*) AS review_count, ROUND(AVG(rating)::numeric, 2) AS rating
                FROM product_reviews, bounds
                WHERE status = 'PUBLISHED'
                  AND created_at >= bounds.period_start
                GROUP BY product_id
            ),
            previous_review_counts AS (
                SELECT product_id, COUNT(*) AS review_count
                FROM product_reviews, bounds
                WHERE status = 'PUBLISHED'
                  AND created_at >= bounds.previous_start
                  AND created_at < bounds.period_start
                GROUP BY product_id
            ),
            view_stats AS (
                SELECT 
                    product_id,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 day') AS view_24h,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') AS view_7d,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') AS view_30d,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '365 days') AS view_1y
                FROM product_view_events
                WHERE created_at >= NOW() - INTERVAL '365 days'
                GROUP BY product_id
            ),
            search_stats AS (
                SELECT 
                    product_id,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 day') AS search_24h,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') AS search_7d,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') AS search_30d,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '365 days') AS search_1y
                FROM product_search_events
                WHERE created_at >= NOW() - INTERVAL '365 days' AND product_id IS NOT NULL
                GROUP BY product_id
            ),
            sales_stats AS (
                SELECT 
                    oi.product_id,
                    SUM(CASE WHEN o.created_at >= NOW() - INTERVAL '1 day' THEN oi.quantity ELSE 0 END) AS sold_24h,
                    SUM(CASE WHEN o.created_at >= NOW() - INTERVAL '7 days' THEN oi.quantity ELSE 0 END) AS sold_7d,
                    SUM(CASE WHEN o.created_at >= NOW() - INTERVAL '30 days' THEN oi.quantity ELSE 0 END) AS sold_30d,
                    SUM(CASE WHEN o.created_at >= NOW() - INTERVAL '365 days' THEN oi.quantity ELSE 0 END) AS sold_1y
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.status = 'COMPLETED' AND o.created_at >= NOW() - INTERVAL '365 days'
                GROUP BY oi.product_id
            ),
            like_stats AS (
                SELECT 
                    product_id,
                    COALESCE(SUM(CASE WHEN action = 'LIKE' THEN 1 ELSE -1 END) FILTER (WHERE created_at >= NOW() - INTERVAL '1 day'), 0) AS like_24h,
                    COALESCE(SUM(CASE WHEN action = 'LIKE' THEN 1 ELSE -1 END) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days'), 0) AS like_7d,
                    COALESCE(SUM(CASE WHEN action = 'LIKE' THEN 1 ELSE -1 END) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days'), 0) AS like_30d,
                    COALESCE(SUM(CASE WHEN action = 'LIKE' THEN 1 ELSE -1 END) FILTER (WHERE created_at >= NOW() - INTERVAL '365 days'), 0) AS like_1y
                FROM user_favorite_events
                WHERE created_at >= NOW() - INTERVAL '365 days'
                GROUP BY product_id
            ),
            rating_stats AS (
                SELECT 
                    product_id,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 day') AS review_24h,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') AS review_7d,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') AS review_30d,
                    COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '365 days') AS review_1y,
                    COALESCE(AVG(rating) FILTER (WHERE created_at >= NOW() - INTERVAL '1 day'), 0.0) AS rating_24h,
                    COALESCE(AVG(rating) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days'), 0.0) AS rating_7d,
                    COALESCE(AVG(rating) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days'), 0.0) AS rating_30d,
                    COALESCE(AVG(rating) FILTER (WHERE created_at >= NOW() - INTERVAL '365 days'), 0.0) AS rating_1y
                FROM product_reviews
                WHERE status = 'PUBLISHED' AND created_at >= NOW() - INTERVAL '365 days'
                GROUP BY product_id
            ),
            metric_history AS (
                SELECT
                    p.id AS product_id,
                    jsonb_agg(
                        jsonb_build_object(
                            'label', to_char(bucket.bucket_start, CASE WHEN CAST(:period_days AS integer) <= 1 THEN 'HH24:00' WHEN CAST(:period_days AS integer) <= 30 THEN 'DD/MM' ELSE 'MM/YYYY' END),
                            'searchCount', COALESCE(search_bucket.count_value, 0),
                            'viewCount', COALESCE(view_bucket.count_value, 0),
                            'likeCount', COALESCE(like_bucket.count_value, 0),
                            'periodSoldCount', COALESCE(sales_bucket.count_value, 0),
                            'trendScore', ROUND((COALESCE(view_bucket.count_value, 0) * 0.35 + COALESCE(search_bucket.count_value, 0) * 0.25 + COALESCE(sales_bucket.count_value, 0) * 0.25 + COALESCE(like_bucket.count_value, 0) * 0.1)::numeric, 2)
                        )
                        ORDER BY bucket.bucket_start
                    ) AS history
                FROM products p
                CROSS JOIN bounds
                CROSS JOIN LATERAL generate_series(bounds.chart_start, bounds.chart_end, bounds.bucket_size) AS bucket(bucket_start)
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS count_value
                    FROM product_view_events pve
                    WHERE pve.product_id = p.id
                      AND pve.created_at >= bucket.bucket_start
                      AND pve.created_at < bucket.bucket_start + bounds.bucket_size
                ) view_bucket ON TRUE
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS count_value
                    FROM product_search_events pse
                    WHERE pse.product_id = p.id
                      AND pse.created_at >= bucket.bucket_start
                      AND pse.created_at < bucket.bucket_start + bounds.bucket_size
                ) search_bucket ON TRUE
                LEFT JOIN LATERAL (
                    SELECT COALESCE(SUM(CASE WHEN ufe.action = 'LIKE' THEN 1 ELSE -1 END), 0) AS count_value
                    FROM user_favorite_events ufe
                    WHERE ufe.product_id = p.id
                      AND ufe.created_at >= bucket.bucket_start
                      AND ufe.created_at < bucket.bucket_start + bounds.bucket_size
                ) like_bucket ON TRUE
                LEFT JOIN LATERAL (
                    SELECT COALESCE(SUM(oi.quantity), 0) AS count_value
                    FROM order_items oi
                    JOIN orders o ON o.id = oi.order_id
                    WHERE oi.product_id = p.id
                      AND o.status = 'COMPLETED'
                      AND o.created_at >= bucket.bucket_start
                      AND o.created_at < bucket.bucket_start + bounds.bucket_size
                ) sales_bucket ON TRUE
                WHERE p.status = 'ACTIVE'
                GROUP BY p.id
            )
            SELECT
                p.id::text,
                p.sku,
                p.name,
                p.slug,
                p.category,
                p.brand,
                c.id::text AS "categoryId",
                c.parent_id::text AS "categoryParentId",
                c.slug AS "categorySlug",
                c.name AS "categoryName",
                COALESCE(c.spec_fields, '[]'::jsonb) || COALESCE(sc.spec_fields, '[]'::jsonb) AS "specFields",
                sc.id::text AS "subcategoryId",
                sc.parent_id::text AS "subcategoryParentId",
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
                COALESCE(period_review_stats.rating, 0.0) AS rating,
                COALESCE(all_review_stats.review_count, 0) AS "reviewCount",
                COALESCE(all_favorite_counts.favorite_count, 0) AS "favoriteCount",
                COALESCE(all_sales.sold_count, 0) AS "soldCount",
                COALESCE(period_sales.sold_count, 0) AS "periodSoldCount",
                COALESCE(period_sales.revenue, 0) AS "periodRevenue",
                COALESCE(previous_period_sales.sold_count, 0) AS "previousPeriodSoldCount",
                COALESCE(search_counts.search_count, 0) AS "searchCount",
                COALESCE(view_counts.view_count, 0) AS "viewCount",
                COALESCE(previous_search_counts.search_count, 0) AS "previousSearchCount",
                COALESCE(previous_view_counts.view_count, 0) AS "previousViewCount",
                COALESCE(period_like_counts.like_count, 0) AS "periodLikeCount",
                COALESCE(previous_like_counts.like_count, 0) AS "previousPeriodLikeCount",
                COALESCE(period_review_stats.review_count, 0) AS "periodReviewCount",
                COALESCE(previous_review_counts.review_count, 0) AS "previousPeriodReviewCount",
                COALESCE(vs.view_24h, 0) AS "view24h",
                COALESCE(vs.view_7d, 0) AS "view7d",
                COALESCE(vs.view_30d, 0) AS "view30d",
                COALESCE(vs.view_1y, 0) AS "view1y",
                COALESCE(ss.search_24h, 0) AS "search24h",
                COALESCE(ss.search_7d, 0) AS "search7d",
                COALESCE(ss.search_30d, 0) AS "search30d",
                COALESCE(ss.search_1y, 0) AS "search1y",
                COALESCE(sls.sold_24h, 0) AS "sold24h",
                COALESCE(sls.sold_7d, 0) AS "sold7d",
                COALESCE(sls.sold_30d, 0) AS "sold30d",
                COALESCE(sls.sold_1y, 0) AS "sold1y",
                COALESCE(lk.like_24h, 0) AS "like24h",
                COALESCE(lk.like_7d, 0) AS "like7d",
                COALESCE(lk.like_30d, 0) AS "like30d",
                COALESCE(lk.like_1y, 0) AS "like1y",
                COALESCE(rt.review_24h, 0) AS "review24h",
                COALESCE(rt.review_7d, 0) AS "review7d",
                COALESCE(rt.review_30d, 0) AS "review30d",
                COALESCE(rt.review_1y, 0) AS "review1y",
                COALESCE(rt.rating_24h, 0.0) AS "rating24h",
                COALESCE(rt.rating_7d, 0.0) AS "rating7d",
                COALESCE(rt.rating_30d, 0.0) AS "rating30d",
                COALESCE(rt.rating_1y, 0.0) AS "rating1y",
                COALESCE(metric_history.history, '[]'::jsonb) AS history,
                p.is_featured AS "isFeatured",
                p.is_flash_sale AS "isFlashSale",
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
                            'price', pv.price,
                            'salePrice', pv.sale_price,
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
            LEFT JOIN (
                SELECT oi.product_id, SUM(oi.quantity) AS sold_count
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.status = 'COMPLETED'
                GROUP BY oi.product_id
            ) all_sales ON all_sales.product_id = p.id
            LEFT JOIN (
                SELECT oi.product_id, SUM(oi.quantity) AS sold_count, SUM(oi.total_price) AS revenue
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.status = 'COMPLETED'
                  AND o.created_at >= NOW() - (CAST(:period_days AS integer) * INTERVAL '1 day')
                GROUP BY oi.product_id
            ) period_sales ON period_sales.product_id = p.id
            LEFT JOIN (
                SELECT oi.product_id, SUM(oi.quantity) AS sold_count
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.status = 'COMPLETED'
                  AND o.created_at >= NOW() - (CAST(:period_days AS integer) * INTERVAL '2 day')
                  AND o.created_at < NOW() - (CAST(:period_days AS integer) * INTERVAL '1 day')
                GROUP BY oi.product_id
            ) previous_period_sales ON previous_period_sales.product_id = p.id
            LEFT JOIN search_counts ON search_counts.product_id = p.id
            LEFT JOIN view_counts ON view_counts.product_id = p.id
            LEFT JOIN previous_search_counts ON previous_search_counts.product_id = p.id
            LEFT JOIN previous_view_counts ON previous_view_counts.product_id = p.id
            LEFT JOIN all_favorite_counts ON all_favorite_counts.product_id = p.id
            LEFT JOIN all_review_stats ON all_review_stats.product_id = p.id
            LEFT JOIN period_like_counts ON period_like_counts.product_id = p.id
            LEFT JOIN previous_like_counts ON previous_like_counts.product_id = p.id
            LEFT JOIN period_review_stats ON period_review_stats.product_id = p.id
            LEFT JOIN previous_review_counts ON previous_review_counts.product_id = p.id
            LEFT JOIN view_stats vs ON vs.product_id = p.id
            LEFT JOIN search_stats ss ON ss.product_id = p.id
            LEFT JOIN sales_stats sls ON sls.product_id = p.id
            LEFT JOIN like_stats lk ON lk.product_id = p.id
            LEFT JOIN rating_stats rt ON rt.product_id = p.id
            LEFT JOIN metric_history ON metric_history.product_id = p.id
            WHERE p.status = 'ACTIVE'
            GROUP BY p.id, c.id, sc.id, all_sales.sold_count, period_sales.sold_count, period_sales.revenue,
                previous_period_sales.sold_count, search_counts.search_count, view_counts.view_count,
                previous_search_counts.search_count, previous_view_counts.view_count, metric_history.history,
                all_favorite_counts.favorite_count, all_review_stats.review_count,
                period_review_stats.rating,
                period_like_counts.like_count, previous_like_counts.like_count,
                period_review_stats.review_count, previous_review_counts.review_count,
                vs.view_24h, vs.view_7d, vs.view_30d, vs.view_1y,
                ss.search_24h, ss.search_7d, ss.search_30d, ss.search_1y,
                sls.sold_24h, sls.sold_7d, sls.sold_30d, sls.sold_1y,
                lk.like_24h, lk.like_7d, lk.like_30d, lk.like_1y,
                rt.review_24h, rt.review_7d, rt.review_30d, rt.review_1y,
                rt.rating_24h, rt.rating_7d, rt.rating_30d, rt.rating_1y
            ORDER BY p.created_at DESC
            """
        ),
        {"period_days": period_days},
    )
    rows = [ranking_row(row) for row in result]
    if category and category != "all":
        rows = [row for row in rows if product_matches_category(row, category)]

    if criteria == "trending":
        rows.sort(
            key=lambda item: (
                item.get("trendScore") or 0.0,
                item.get("score24h") or 0.0,
                item.get("score7d") or 0.0,
                item.get("score30d") or 0.0,
                item.get("score1y") or 0.0,
                item.get("periodRevenue") or 0.0,
                item.get("rating") or 0.0,
            ),
            reverse=True,
        )
    elif criteria == "sold":
        rows.sort(
            key=lambda item: (
                item.get("periodSoldCount") or 0,
                item.get("sold24h") or 0,
                item.get("sold7d") or 0,
                item.get("sold30d") or 0,
                item.get("sold1y") or 0,
                item.get("periodRevenue") or 0.0,
                item.get("rating") or 0.0,
            ),
            reverse=True,
        )
    elif criteria == "view":
        rows.sort(
            key=lambda item: (
                item.get("viewCount") or 0,
                item.get("view24h") or 0,
                item.get("view7d") or 0,
                item.get("view30d") or 0,
                item.get("view1y") or 0,
                item.get("periodRevenue") or 0.0,
                item.get("rating") or 0.0,
            ),
            reverse=True,
        )
    elif criteria == "search":
        rows.sort(
            key=lambda item: (
                item.get("searchCount") or 0,
                item.get("search24h") or 0,
                item.get("search7d") or 0,
                item.get("search30d") or 0,
                item.get("search1y") or 0,
                item.get("periodRevenue") or 0.0,
                item.get("rating") or 0.0,
            ),
            reverse=True,
        )
    elif criteria == "like":
        rows.sort(
            key=lambda item: (
                item.get("periodLikeCount") or 0,
                item.get("like24h") or 0,
                item.get("like7d") or 0,
                item.get("like30d") or 0,
                item.get("like1y") or 0,
                item.get("periodRevenue") or 0.0,
                item.get("rating") or 0.0,
            ),
            reverse=True,
        )
    elif criteria == "rating":
        rows.sort(
            key=lambda item: (
                item.get("rating") or 0.0,
                item.get("rating24h") or 0.0,
                item.get("rating7d") or 0.0,
                item.get("rating30d") or 0.0,
                item.get("rating1y") or 0.0,
                item.get("periodRevenue") or 0.0,
                item.get("periodReviewCount") or 0,
            ),
            reverse=True,
        )
    else:
        order_field = RANKING_ORDER_FIELDS[criteria]
        rows.sort(key=lambda item: (item.get(order_field) or 0, item.get("periodRevenue") or 0, item.get("rating") or 0), reverse=True)
    return rows[:limit]


@router.get("/images")
async def list_product_images(
    session: AsyncSession = Depends(get_session),
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
) -> dict:
    products = await list_products(
        session=session,
        q=None,
        category=None,
        brand=None,
        min_price=None,
        max_price=None,
        sort="default",
        limit=None,
        offset=0,
        flash_sale=None,
        featured=None,
    )
    collection = build_product_image_collection(products, q=q, category=category)
    items = collection["items"]
    total_products = len(items)
    start = (page - 1) * limit
    paged_items = items[start:start + limit]
    return {
        "items": paged_items,
        "categories": collection["categories"],
        "totalImages": collection["totalImages"],
        "totalProducts": total_products,
        "page": page,
        "limit": limit,
        "totalPages": max(1, (total_products + limit - 1) // limit),
        "hasMore": start + limit < total_products,
    }


@router.get("/images/resolve/{view_id}")
async def resolve_product_image(
    view_id: str,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=30, ge=1, le=100),
) -> dict:
    products = await list_products(
        session=session,
        q=None,
        category=None,
        brand=None,
        min_price=None,
        max_price=None,
        sort="default",
        limit=None,
        offset=0,
        flash_sale=None,
        featured=None,
    )
    items = build_product_image_collection(products)["items"]

    for item_index, item in enumerate(items):
        image_index = 0
        if item["id"] != view_id:
            image_index = next((index for index, image in enumerate(item["images"]) if image["id"] == view_id), -1)
            if image_index < 0:
                continue

        return {
            "item": item,
            "imageIndex": image_index,
            "imageId": item["images"][image_index]["id"],
            "page": item_index // limit + 1,
            "limit": limit,
        }

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found.")


@router.post("/search-intent", response_model=ProductSearchIntentResponse)
async def parse_search_intent(payload: ProductSearchIntentRequest) -> ProductSearchIntentResponse:
    return await parse_product_search_intent(payload)


@router.get("/products/{product_id}")
async def get_product(product_id: str, session: AsyncSession = Depends(get_session)) -> dict:
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
                            'price', pv.price,
                            'salePrice', pv.sale_price,
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
            LEFT JOIN (
                SELECT oi.product_id, SUM(oi.quantity) AS sold_count
                FROM order_items oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.status = 'COMPLETED'
                GROUP BY oi.product_id
            ) os ON os.product_id = p.id
            WHERE p.status = 'ACTIVE' AND (p.id::text = :product_id OR p.slug = :product_id)
            GROUP BY p.id, c.id, sc.id, os.sold_count
            """
        ),
        {"product_id": product_id},
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    
    p_dict = product_row(row)
    sales_config = p_dict.get("salesConfig") or {}
    offers = sales_config.get("accessoryOffers", []) or []
    if offers:
        accessory_ids = []
        for o in offers:
            if isinstance(o, dict) and o.get("productId"):
                try:
                    accessory_ids.append(UUID(str(o["productId"])))
                except ValueError:
                    continue
        
        if accessory_ids:
            acc_result = await session.execute(
                text(
                    """
                    SELECT id::text, sku, name, price, sale_price AS "salePrice", image_url AS "imageUrl"
                    FROM products
                    WHERE id IN :ids AND status = 'ACTIVE' AND deleted_at IS NULL
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": accessory_ids}
            )
            acc_rows = {r["id"]: dict(r) for r in acc_result.mappings().all()}
            
            resolved_offers = []
            for o in offers:
                if not isinstance(o, dict):
                    continue
                prod_id = str(o.get("productId") or "")
                acc_meta = acc_rows.get(prod_id)
                if acc_meta:
                    discount_type = str(o.get("discountType") or "PERCENT").upper()
                    discount_value = float(o.get("discountValue") or 0)
                    
                    sale_price = float(acc_meta.get("salePrice") if acc_meta.get("salePrice") is not None else acc_meta.get("price") or 0)
                    original_price = float(acc_meta.get("price") or 0)
                    
                    if discount_type == "PERCENT":
                        bundle_price = sale_price * (1.0 - (discount_value / 100.0))
                    else:  # FIXED
                        bundle_price = max(0.0, sale_price - discount_value)
                        
                    resolved_offers.append({
                        "productId": prod_id,
                        "discountType": discount_type,
                        "discountValue": discount_value,
                        "maxQuantity": int(o.get("maxQuantity") or 1),
                        "productName": acc_meta.get("name", ""),
                        "productSku": acc_meta.get("sku", ""),
                        "imageUrl": acc_meta.get("imageUrl", ""),
                        "originalPrice": original_price,
                        "salePrice": sale_price,
                        "price": round(bundle_price)
                    })
            sales_config["accessoryOffers"] = resolved_offers
            p_dict["salesConfig"] = sales_config

    return p_dict


@router.post("/products/{product_id}/view", status_code=status.HTTP_201_CREATED)
async def record_product_view_heartbeat(
    product_id: str,
    payload: ProductAnalyticsEventRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    product_uuid = await session.scalar(
        text("SELECT id FROM products WHERE status = 'ACTIVE' AND (id::text = :product_id OR slug = :product_id)"),
        {"product_id": product_id},
    )
    if product_uuid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    identity = product_view_identity(payload, request)
    valid_key = f"product_view:valid:{product_uuid}:{identity}"
    state_key = f"product_view:state:{product_uuid}:{identity}"
    delta_seconds = max(0, min(int(payload.activeSeconds or 0), 60))

    try:
        if await redis.exists(valid_key):
            return {"counted": False, "reason": "deduped", "validAfterSeconds": PRODUCT_VIEW_VALID_SECONDS}

        accumulated_seconds = int(await redis.hincrby(state_key, "active_seconds", delta_seconds) or 0)
        await redis.hset(state_key, mapping={
            "scroll_depth": max(float(payload.scrollDepth or 0), float(await redis.hget(state_key, "scroll_depth") or 0)),
            "source": payload.source or "",
            "last_seen_at": int(time.time()),
        })
        await redis.expire(state_key, PRODUCT_VIEW_STATE_TTL_SECONDS)

        qualifies = (
            accumulated_seconds >= PRODUCT_VIEW_VALID_SECONDS
            or float(payload.scrollDepth or 0) >= PRODUCT_VIEW_VALID_SCROLL_DEPTH
        )
        if not qualifies:
            return {
                "counted": False,
                "activeSeconds": accumulated_seconds,
                "validAfterSeconds": PRODUCT_VIEW_VALID_SECONDS,
            }

        if not await redis.set(valid_key, "1", ex=PRODUCT_VIEW_DEDUPE_SECONDS, nx=True):
            return {"counted": False, "reason": "deduped", "validAfterSeconds": PRODUCT_VIEW_VALID_SECONDS}
        await insert_valid_product_view(
            session=session,
            product_id=product_uuid,
            payload=payload,
            request=request,
            accumulated_seconds=accumulated_seconds,
        )
        await redis.delete(state_key)
        return {"counted": True, "activeSeconds": accumulated_seconds}
    except Exception:
        existing = await session.scalar(
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
                "product_id": product_uuid,
                "device_id": payload.deviceId,
                "session_id": payload.sessionId,
                "ip_address": request_ip(request),
                "user_agent": request.headers.get("user-agent"),
            },
        )
        if existing:
            return {"counted": False, "reason": "deduped", "validAfterSeconds": PRODUCT_VIEW_VALID_SECONDS}
        if delta_seconds >= PRODUCT_VIEW_VALID_SECONDS or payload.scrollDepth >= PRODUCT_VIEW_VALID_SCROLL_DEPTH:
            await insert_valid_product_view(
                session=session,
                product_id=product_uuid,
                payload=payload,
                request=request,
                accumulated_seconds=delta_seconds,
            )
            return {"counted": True, "activeSeconds": delta_seconds, "mode": "fallback"}
        return {"counted": False, "activeSeconds": delta_seconds, "validAfterSeconds": PRODUCT_VIEW_VALID_SECONDS}


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
        await session.execute(
            text(
                """
                INSERT INTO product_search_events (query, normalized_query, session_id, ip_address, user_agent, result_count)
                VALUES (:query, :normalized_query, :session_id, :ip_address, :user_agent, :result_count)
                """
            ),
            {
                "query": query,
                "normalized_query": normalized_query,
                "session_id": payload.sessionId,
                "ip_address": request_ip(request),
                "user_agent": request.headers.get("user-agent"),
                "result_count": payload.resultCount or 0,
            },
        )
    else:
        for product_id in product_ids:
            await session.execute(
                text(
                    """
                    INSERT INTO product_search_events (query, normalized_query, product_id, session_id, ip_address, user_agent, result_count)
                    VALUES (:query, :normalized_query, :product_id, :session_id, :ip_address, :user_agent, :result_count)
                    """
                ),
                {
                    "query": query,
                    "normalized_query": normalized_query,
                    "product_id": product_id,
                    "session_id": payload.sessionId,
                    "ip_address": request_ip(request),
                    "user_agent": request.headers.get("user-agent"),
                    "result_count": payload.resultCount or 0,
                },
            )
    await session.commit()
    return {"counted": True, "productCount": len(product_ids)}


@router.post("/products/{product_id}/favorite", status_code=status.HTTP_200_OK)
async def toggle_favorite(
    product_id: UUID,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    await enforce_favorite_toggle_rate_limit(
        redis=redis,
        user_id=current_user_id,
        product_id=product_id,
    )

    row = (await session.execute(
        text(
            """
            SELECT id, is_active
            FROM user_favorites
            WHERE user_id = :user_id AND product_id = :product_id
            """
        ),
        {"user_id": current_user_id, "product_id": product_id}
    )).first()

    if row and row.is_active:
        await session.execute(
            text(
                """
                UPDATE user_favorites
                SET is_active = FALSE, updated_at = NOW()
                WHERE user_id = :user_id AND product_id = :product_id
                """
            ),
            {"user_id": current_user_id, "product_id": product_id}
        )
        await session.execute(
            text(
                """
                INSERT INTO user_favorite_events (user_id, product_id, action)
                VALUES (:user_id, :product_id, 'UNLIKE')
                """
            ),
            {"user_id": current_user_id, "product_id": product_id}
        )
        await session.execute(
            text("UPDATE products SET favorite_count = favorite_count - 1 WHERE id = :product_id AND favorite_count > 0"),
            {"product_id": product_id}
        )
        await session.commit()
        return {"favorited": False}
    else:
        if row:
            await session.execute(
                text(
                    """
                    UPDATE user_favorites
                    SET is_active = TRUE, created_at = NOW(), updated_at = NOW()
                    WHERE user_id = :user_id AND product_id = :product_id
                    """
                ),
                {"user_id": current_user_id, "product_id": product_id}
            )
        else:
            await session.execute(
                text("INSERT INTO user_favorites (user_id, product_id) VALUES (:user_id, :product_id)"),
                {"user_id": current_user_id, "product_id": product_id}
            )
        await session.execute(
            text(
                """
                INSERT INTO user_favorite_events (user_id, product_id, action)
                VALUES (:user_id, :product_id, 'LIKE')
                """
            ),
            {"user_id": current_user_id, "product_id": product_id}
        )
        await session.execute(
            text("UPDATE products SET favorite_count = favorite_count + 1 WHERE id = :product_id"),
            {"product_id": product_id}
        )
        await session.commit()
        return {"favorited": True}


@router.get("/favorites", status_code=status.HTTP_200_OK)
async def list_favorites(
    session: AsyncSession = Depends(get_session),
    current_user_id: UUID = Depends(get_current_user_id),
) -> list[dict]:
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
        {"user_id": current_user_id}
    )
    items = []
    for row in result:
        item = product_row(row)
        row_dict = dict(row._mapping)
        favorited_at = row_dict.get("favoritedAt")
        favorite_updated_at = row_dict.get("favoriteUpdatedAt")
        item["favoritedAt"] = favorited_at.isoformat() if favorited_at else None
        item["favoriteUpdatedAt"] = favorite_updated_at.isoformat() if favorite_updated_at else None
        items.append(item)
    return items


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(payload: CreateProductRequest, session: AsyncSession = Depends(get_session)) -> dict:
    product_id = uuid4()
    slug = f"{payload.name.lower().replace(' ', '-')}-{product_id.hex[:6]}"
    category = payload.category if payload.category in {"PHONE", "LAPTOP", "ACCESSORY"} else "ACCESSORY"
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
            "sku": f"SKU-{product_id.hex[:10].upper()}",
            "name": payload.name,
            "slug": slug,
            "category": category,
            "brand": payload.brand,
            "description": payload.description or "Mô tả chi tiết",
            "price": payload.price,
            "sale_price": payload.discountPrice,
            "image_url": payload.imageUrl,
        },
    )
    await session.commit()
    return {"id": str(product_id)}
