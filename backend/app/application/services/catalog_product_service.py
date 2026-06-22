from uuid import UUID, uuid4
import time

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.catalog_utils import (
    CreateProductRequest,
    ProductAnalyticsEventRequest,
    PRODUCT_VIEW_DEDUPE_SECONDS,
    PRODUCT_VIEW_STATE_TTL_SECONDS,
    PRODUCT_VIEW_VALID_SCROLL_DEPTH,
    PRODUCT_VIEW_VALID_SECONDS,
    enforce_favorite_toggle_rate_limit,
    build_flash_sale_meta,
    insert_valid_product_view,
    product_row,
    product_view_identity,
    request_ip,
)
from app.infrastructure.database.repositories import catalog_product_repo


async def get_product(product_id: str, session: AsyncSession) -> dict:
    row = await catalog_product_repo.get_active_product_detail(session, product_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")

    p_dict = product_row(row)
    sales_config = p_dict.get("salesConfig") or {}
    if p_dict.get("status") == "DISCONTINUED":
        sales_config["accessoryOffers"] = []
        sales_config["attachedServices"] = []
        p_dict["salesConfig"] = sales_config
        return p_dict

    product_uuid = UUID(str(p_dict["id"]))
    attached_services = await catalog_product_repo.list_product_attached_services(session, product_uuid)
    if not attached_services:
        fallback_service_ids = []
        for item in sales_config.get("attachedServices", []) or []:
            if not isinstance(item, dict) or not item.get("serviceId"):
                continue
            try:
                fallback_service_ids.append(UUID(str(item["serviceId"])))
            except ValueError:
                continue
        attached_services = await catalog_product_repo.list_active_attached_services_by_ids(session, fallback_service_ids)
    sales_config["attachedServices"] = attached_services

    offers = sales_config.get("accessoryOffers", []) or []
    if offers:
        accessory_ids = []
        for offer in offers:
            if isinstance(offer, dict) and offer.get("productId"):
                try:
                    accessory_ids.append(UUID(str(offer["productId"])))
                except ValueError:
                    continue

        acc_rows = await catalog_product_repo.list_active_accessories(session, accessory_ids)
        resolved_offers = []
        for offer in offers:
            if not isinstance(offer, dict):
                continue
            prod_id = str(offer.get("productId") or "")
            acc_meta = acc_rows.get(prod_id)
            if not acc_meta:
                continue

            discount_type = str(offer.get("discountType") or "PERCENT").upper()
            discount_value = float(offer.get("discountValue") or 0)
            original_price = float(acc_meta.get("price") or 0)
            normal_sale_price = float(acc_meta["salePrice"]) if acc_meta.get("salePrice") is not None else None
            current_price = normal_sale_price if normal_sale_price is not None and normal_sale_price > 0 else original_price
            flash_sale = build_flash_sale_meta(acc_meta, current_price)
            effective_price = float(flash_sale["salePrice"]) if flash_sale else current_price
            bundle_price = effective_price * (1.0 - (discount_value / 100.0)) if discount_type == "PERCENT" else max(0.0, effective_price - discount_value)
            resolved_offers.append(
                {
                    "productId": prod_id,
                    "discountType": discount_type,
                    "discountValue": discount_value,
                    "maxQuantity": int(offer.get("maxQuantity") or 1),
                    "productName": acc_meta.get("name", ""),
                    "productSku": acc_meta.get("sku", ""),
                    "imageUrl": acc_meta.get("imageUrl", ""),
                    "originalPrice": original_price,
                    "salePrice": effective_price,
                    "flashSale": flash_sale,
                    "price": round(bundle_price),
                }
            )
        sales_config["accessoryOffers"] = resolved_offers
        p_dict["salesConfig"] = sales_config

    return p_dict


async def record_product_view_heartbeat(
    product_id: str,
    payload: ProductAnalyticsEventRequest,
    request: Request,
    session: AsyncSession,
    redis: Redis,
) -> dict:
    product_uuid = await catalog_product_repo.get_active_product_uuid(session, product_id)
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
        await redis.hset(
            state_key,
            mapping={
                "scroll_depth": max(float(payload.scrollDepth or 0), float(await redis.hget(state_key, "scroll_depth") or 0)),
                "source": payload.source or "",
                "last_seen_at": int(time.time()),
            },
        )
        await redis.expire(state_key, PRODUCT_VIEW_STATE_TTL_SECONDS)

        qualifies = accumulated_seconds >= PRODUCT_VIEW_VALID_SECONDS or float(payload.scrollDepth or 0) >= PRODUCT_VIEW_VALID_SCROLL_DEPTH
        if not qualifies:
            return {"counted": False, "activeSeconds": accumulated_seconds, "validAfterSeconds": PRODUCT_VIEW_VALID_SECONDS}

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
        existing = await catalog_product_repo.has_recent_product_view_event(
            session,
            product_id=product_uuid,
            device_id=payload.deviceId,
            session_id=payload.sessionId,
            ip_address=request_ip(request),
            user_agent=request.headers.get("user-agent"),
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


async def toggle_favorite(product_id: UUID, session: AsyncSession, redis: Redis, current_user_id: UUID) -> dict:
    await enforce_favorite_toggle_rate_limit(redis=redis, user_id=current_user_id, product_id=product_id)
    row = await catalog_product_repo.get_user_favorite(session, user_id=current_user_id, product_id=product_id)
    if row and row.is_active:
        await catalog_product_repo.deactivate_favorite(session, user_id=current_user_id, product_id=product_id)
        await session.commit()
        return {"favorited": False}

    await catalog_product_repo.activate_favorite(session, user_id=current_user_id, product_id=product_id, exists=bool(row))
    await session.commit()
    return {"favorited": True}


async def list_favorites(session: AsyncSession, current_user_id: UUID) -> list[dict]:
    rows = await catalog_product_repo.list_favorites(session, current_user_id)
    items = []
    for row in rows:
        item = product_row(row)
        row_dict = dict(row._mapping)
        favorited_at = row_dict.get("favoritedAt")
        favorite_updated_at = row_dict.get("favoriteUpdatedAt")
        item["favoritedAt"] = favorited_at.isoformat() if favorited_at else None
        item["favoriteUpdatedAt"] = favorite_updated_at.isoformat() if favorite_updated_at else None
        items.append(item)
    return items


async def create_product(payload: CreateProductRequest, session: AsyncSession) -> dict:
    product_id = uuid4()
    slug = f"{payload.name.lower().replace(' ', '-')}-{product_id.hex[:6]}"
    category = payload.category if payload.category in {"PHONE", "LAPTOP", "ACCESSORY"} else "ACCESSORY"
    await catalog_product_repo.insert_draft_product(
        session,
        product_id=product_id,
        sku=f"SKU-{product_id.hex[:10].upper()}",
        name=payload.name,
        slug=slug,
        category=category,
        brand=payload.brand,
        description=payload.description or "Mô tả chi tiết",
        price=payload.price,
        sale_price=payload.discountPrice,
        image_url=payload.imageUrl,
    )
    await session.commit()
    return {"id": str(product_id)}
