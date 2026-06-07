import json
import time
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import get_session
from app.infrastructure.cache import get_redis
from app.infrastructure.database.repositories import catalog_category_repo

router = APIRouter(tags=["Catalog"])

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
    categories = await catalog_category_repo.list_active_root_categories(session)
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
    row = await catalog_category_repo.get_category_redirect(session, old_slug)
    if not row:
        raise HTTPException(status_code=404, detail="Redirect not found.")
    return row
