import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.catalog import product_row
from app.infrastructure.cache import get_redis
from app.infrastructure.database.repositories import storefront_repo
from app.infrastructure.database.session import get_session


router = APIRouter(prefix="/storefront", tags=["Storefront"])


async def resolve_brand_redirect(session: AsyncSession, slug: str, max_hops: int = 5) -> str | None:
    current = slug
    seen = {slug}
    for _ in range(max_hops):
        next_slug = await storefront_repo.get_brand_redirect_slug(session, current)
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
    brand = await storefront_repo.get_active_brand_by_slug(session, slug)
    if not brand:
        redirect = await resolve_brand_redirect(session, slug)
        if redirect:
            response.status_code = status.HTTP_308_PERMANENT_REDIRECT
            response.headers["Location"] = f"/api/storefront/brands/{redirect}"
            return {"redirectTo": redirect}
        raise HTTPException(status_code=404, detail="Brand not found.")

    cache_key = f"storefront:brand:{brand['slug']}:v:{brand['cacheVersion']}:page:{page}:limit:{limit}"
    try:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    total = await storefront_repo.count_active_products_by_brand(session, brand_id=brand["id"], brand_name=brand["name"])
    product_result = await storefront_repo.list_active_products_by_brand(
        session,
        brand_id=brand["id"],
        brand_name=brand["name"],
        limit=limit,
        offset=(page - 1) * limit,
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
