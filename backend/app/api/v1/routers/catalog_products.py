from uuid import UUID, uuid4
import time
from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id
from app.infrastructure.database.session import get_session
from app.infrastructure.cache import get_redis
from app.api.v1.routers.catalog_utils import (
    CreateProductRequest,
    ProductAnalyticsEventRequest,
    PRODUCT_VIEW_VALID_SECONDS,
    PRODUCT_VIEW_VALID_SCROLL_DEPTH,
    PRODUCT_VIEW_DEDUPE_SECONDS,
    PRODUCT_VIEW_STATE_TTL_SECONDS,
    product_view_identity,
    request_ip,
    insert_valid_product_view,
    product_row,
    enforce_favorite_toggle_rate_limit,
)

router = APIRouter()

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
            WHERE p.status = 'ACTIVE' AND (p.id::text = :product_id OR p.slug = :product_id)
            GROUP BY p.id, c.id, sc.id, os.sold_count, review_stats.rating, review_stats.review_count,
                favorite_counts.favorite_count, fs.id, fs.discount_type, fs.discount_value, fs.starts_at, fs.ends_at
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
