import json
import re
import time
import unicodedata
from uuid import UUID, uuid4
from fastapi import Request, HTTPException, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.repositories import catalog_product_repo

REDIS_RECOVERY_COOLDOWN_SECONDS = 30
FAVORITE_TOGGLE_RATE_LIMIT = 5
FAVORITE_TOGGLE_RATE_WINDOW_SECONDS = 10
_redis_unavailable_until = 0.0

PRODUCT_VIEW_VALID_SECONDS = 30
PRODUCT_VIEW_VALID_SCROLL_DEPTH = 0.5
PRODUCT_VIEW_DEDUPE_SECONDS = 24 * 60 * 60
PRODUCT_VIEW_STATE_TTL_SECONDS = 60 * 60

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
    await catalog_product_repo.insert_product_view_event(
        session,
        product_id=product_id,
        session_id=payload.sessionId,
        device_id=payload.deviceId,
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        source=payload.source,
        duration_seconds=accumulated_seconds,
        scroll_depth=payload.scrollDepth,
    )
    await session.commit()

def compute_flash_sale_price(base_price: float, discount_type: str, discount_value: float) -> float:
    if base_price <= 0:
        return 0.0
    if discount_type == "PERCENT":
        return round(base_price * (1 - discount_value / 100))
    return round(base_price - discount_value)

def build_flash_sale_meta(item: dict, base_price: float) -> dict | None:
    sale_id = item.get("flashSaleId")
    if not sale_id:
        return None
    discount_type = str(item.get("flashSaleDiscountType") or "PERCENT").upper()
    discount_value = float(item.get("flashSaleDiscountValue") or 0)
    sale_price = compute_flash_sale_price(base_price, discount_type, discount_value)
    if sale_price <= 0 or sale_price >= base_price:
        return None
    starts_at = item.get("flashSaleStartsAt")
    ends_at = item.get("flashSaleEndsAt")
    return {
        "id": str(sale_id),
        "discountType": discount_type,
        "discountValue": discount_value,
        "startsAt": starts_at.isoformat() if starts_at else None,
        "endsAt": ends_at.isoformat() if ends_at else None,
        "originalPrice": base_price,
        "salePrice": sale_price,
        "discountPercent": round(((base_price - sale_price) / base_price) * 100),
    }

def apply_flash_sale_to_variant(variant: dict, flash_sale: dict) -> dict:
    variant_item = dict(variant or {})
    variant_base = float(variant_item.get("salePrice") or variant_item.get("price") or 0)
    if variant_base <= 0:
        return variant_item
    sale_price = compute_flash_sale_price(
        variant_base,
        flash_sale.get("discountType") or "PERCENT",
        float(flash_sale.get("discountValue") or 0),
    )
    if sale_price <= 0 or sale_price >= variant_base:
        return variant_item
    variant_item["originalPrice"] = variant_base
    variant_item["salePrice"] = sale_price
    variant_item["flashSale"] = {
        **flash_sale,
        "originalPrice": variant_base,
        "salePrice": sale_price,
        "discountPercent": round(((variant_base - sale_price) / variant_base) * 100),
    }
    return variant_item

def product_row(row) -> dict:
    item = dict(row._mapping)
    stock = item.get("stock") or 0
    stock_state = "IN_STOCK" if int(stock) > 0 else "OUT_OF_STOCK"
    status_value = item.get("status") or "ACTIVE"
    display_status_val = "Hết hàng" if status_value == "ACTIVE" and stock_state == "OUT_OF_STOCK" else {
        "DRAFT": "Nháp thêm",
        "PENDING": "Chờ duyệt",
        "ACTIVE": "Đang bán",
        "INACTIVE": "Tạm ẩn",
        "DISCONTINUED": "Ngừng kinh doanh",
        "ARCHIVED": "Lưu trữ",
    }.get(status_value, status_value)
    base_price = float(item.get("price") or 0)
    normal_sale_price = float(item["discountPrice"]) if item.get("discountPrice") is not None else None
    current_base_price = normal_sale_price if normal_sale_price is not None and normal_sale_price > 0 else base_price
    flash_sale = build_flash_sale_meta(item, current_base_price)
    display_sale_price = flash_sale["salePrice"] if flash_sale else normal_sale_price
    variants = item.get("variants") or []
    if flash_sale and isinstance(variants, list):
        variants = [apply_flash_sale_to_variant(variant, flash_sale) for variant in variants]
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
        "subcategory": item.get("subcategoryName"),
        "subcategorySlug": item.get("subcategorySlug"),
        "specFields": item.get("specFields") or [],
        "brand": item.get("brand"),
        "description": item.get("description"),
        "specs": item.get("specifications") or {},
        "specifications": item.get("specifications") or {},
        "price": base_price,
        "discountPrice": display_sale_price,
        "salePrice": display_sale_price,
        "originalPrice": current_base_price if flash_sale else base_price,
        "stock": stock,
        "stockQuantity": stock,
        "stockState": stock_state,
        "displayStatus": display_status_val,
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
        "isFlashSale": bool(item.get("isFlashSale") or flash_sale),
        "flashSale": flash_sale,
        "status": status_value,
        "salesConfig": item.get("salesConfig") or {},
        "options": item.get("options") or [],
        "variants": variants,
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
        image_entries: list[dict] = []
        seen_urls: set[str] = set()

        def add_image(url: str | None, *, variant: dict | None = None) -> None:
            if not is_real_product_image_url(url) or url in seen_urls:
                return
            seen_urls.add(url)
            entry = {"url": url}
            if variant:
                color_name = variant.get("colorName")
                color_code = variant.get("colorCode")
                configuration = variant.get("configuration")
                if color_name:
                    entry["variantColorName"] = color_name
                if color_code:
                    entry["variantColorCode"] = color_code
                if configuration:
                    entry["variantConfiguration"] = configuration
            image_entries.append(entry)

        for url in list(product.get("images") or []):
            add_image(url)
        if not image_entries:
            add_image(product.get("imageUrl"))
        for variant in product.get("variants") or []:
            add_image(variant.get("imageUrl"), variant=variant)
            for url in variant.get("images") or []:
                add_image(url, variant=variant)
        if not image_entries:
            continue

        category_name = product.get("category") or ""
        category_key = normalize_category_key(category_name)
        if normalized_category and normalized_category != category_key:
            continue

        haystack = normalize_search_text(f"{product.get('name', '')} {product.get('brand', '')} {category_name}")
        if normalized_keyword and normalized_keyword not in haystack:
            continue

        total_images += len(image_entries)
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
                "mainUrl": product.get("imageUrl") if is_real_product_image_url(product.get("imageUrl")) else image_entries[0]["url"],
                "imageCount": len(image_entries),
                "trendScore": approximate_trend_score(product),
                "product": product,
                "images": [
                    {
                        "id": f"{product['id']}-{index}",
                        "url": image["url"],
                        "productId": product["id"],
                        "productName": product.get("name"),
                        "brand": product.get("brand"),
                        "category": category_name,
                        "product": product,
                        "variantColorName": image.get("variantColorName"),
                        "variantColorCode": image.get("variantColorCode"),
                        "variantConfiguration": image.get("variantConfiguration"),
                    }
                    for index, image in enumerate(image_entries)
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
