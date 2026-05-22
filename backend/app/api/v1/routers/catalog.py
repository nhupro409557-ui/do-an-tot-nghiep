from uuid import UUID, uuid4

import json
import time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ai.search_intent import (
    ProductSearchIntentRequest,
    ProductSearchIntentResponse,
    parse_product_search_intent,
)
from app.infrastructure.database.session import get_session
from app.infrastructure.cache import get_redis


router = APIRouter(prefix="/catalog", tags=["Catalog"])
CATEGORY_CACHE_ROOT_ORDER_KEY = "catalog:categories:roots:active"
CATEGORY_CACHE_ROOT_ORDER_STALE_KEY = "catalog:categories:roots:stale"
REDIS_RECOVERY_COOLDOWN_SECONDS = 30
_redis_unavailable_until = 0.0


def category_branch_cache_key(root_id: str, stale: bool = False) -> str:
    return f"catalog:categories:branch:{root_id}:{'stale' if stale else 'active'}"


def redis_cache_available() -> bool:
    return time.perf_counter() >= _redis_unavailable_until


def mark_redis_unavailable() -> None:
    global _redis_unavailable_until
    _redis_unavailable_until = time.perf_counter() + REDIS_RECOVERY_COOLDOWN_SECONDS


class CreateProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: float = Field(ge=0)
    discountPrice: float | None = Field(default=None, ge=0)
    stock: int = Field(default=0, ge=0)
    brand: str = Field(default="Khác", max_length=100)
    category: str = Field(default="ACCESSORY", max_length=50)
    imageUrl: str | None = None
    description: str | None = None


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
        "categorySlug": item.get("categorySlug"),
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
        "soldCount": item.get("soldCount") or 0,
        "isActive": True,
        "isFeatured": item.get("isFeatured"),
        "isFlashSale": item.get("isFlashSale"),
        "status": status_value,
        "variants": item.get("variants") or [],
    }


RANKING_PERIODS = {
    "month": 30,
    "quarter": 90,
    "year": 365,
}


def ranking_row(row) -> dict:
    item = product_row(row)
    item["periodSoldCount"] = int(dict(row._mapping).get("periodSoldCount") or 0)
    item["periodRevenue"] = float(dict(row._mapping).get("periodRevenue") or 0)
    return item


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
async def list_products(session: AsyncSession = Depends(get_session)) -> list[dict]:
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
            LEFT JOIN product_variants pv ON pv.product_id = p.id AND pv.is_active = TRUE
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
    return [product_row(row) for row in result]


@router.get("/rankings")
async def list_rankings(period: str = "month", session: AsyncSession = Depends(get_session)) -> list[dict]:
    period_days = RANKING_PERIODS.get(period)
    if period_days is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ranking period.")

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
                COALESCE(all_sales.sold_count, 0) AS "soldCount",
                COALESCE(period_sales.sold_count, 0) AS "periodSoldCount",
                COALESCE(period_sales.revenue, 0) AS "periodRevenue",
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
            LEFT JOIN product_variants pv ON pv.product_id = p.id AND pv.is_active = TRUE
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
            WHERE p.status = 'ACTIVE' AND COALESCE(period_sales.sold_count, 0) > 0
            GROUP BY p.id, c.id, sc.id, all_sales.sold_count, period_sales.sold_count, period_sales.revenue
            ORDER BY period_sales.sold_count DESC, period_sales.revenue DESC, p.rating DESC NULLS LAST
            LIMIT 10
            """
        ),
        {"period_days": period_days},
    )
    return [ranking_row(row) for row in result]


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
            LEFT JOIN product_variants pv ON pv.product_id = p.id AND pv.is_active = TRUE
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
    return product_row(row)


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
