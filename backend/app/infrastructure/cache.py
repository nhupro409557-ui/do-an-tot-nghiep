from collections.abc import AsyncGenerator
import time

from redis.asyncio import Redis

from app.config import settings

REDIS_BYPASS_SECONDS = 30
_redis_unavailable_until = 0.0


redis_client = Redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
    socket_connect_timeout=0.5,
    socket_timeout=0.5,
)


def redis_is_available() -> bool:
    return time.monotonic() >= _redis_unavailable_until


def mark_redis_unavailable() -> None:
    global _redis_unavailable_until
    _redis_unavailable_until = time.monotonic() + REDIS_BYPASS_SECONDS


async def safe_redis_get(redis: Redis, key: str):
    if not redis_is_available():
        return None
    try:
        return await redis.get(key)
    except Exception:
        mark_redis_unavailable()
        return None


async def safe_redis_setex(redis: Redis, key: str, seconds: int, value: str) -> bool:
    if not redis_is_available():
        return False
    try:
        await redis.set(key, value, ex=seconds)
        return True
    except Exception:
        mark_redis_unavailable()
        return False


async def safe_redis_sadd(redis: Redis, key: str, *values: str) -> bool:
    if not redis_is_available():
        return False
    try:
        await redis.sadd(key, *values)
        return True
    except Exception:
        mark_redis_unavailable()
        return False


async def safe_redis_expire(redis: Redis, key: str, seconds: int) -> bool:
    if not redis_is_available():
        return False
    try:
        await redis.expire(key, seconds)
        return True
    except Exception:
        mark_redis_unavailable()
        return False


async def get_redis() -> AsyncGenerator[Redis, None]:
    yield redis_client
