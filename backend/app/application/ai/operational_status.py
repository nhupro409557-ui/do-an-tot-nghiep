from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.application.ai.local_circuit_breaker import get_local_circuit_status
from app.infrastructure.cache import mark_redis_unavailable, redis_is_available
from app.infrastructure.database.repositories import ai_repo


async def collect_ai_operational_status(
    session: AsyncSession,
    redis: Redis,
    *,
    hours: int = 24,
) -> dict:
    try:
        metrics = await ai_repo.get_ai_operational_metrics(session, hours=hours)
    except SQLAlchemyError as error:
        await session.rollback()
        metrics = {
            "window_hours": hours,
            "error": f"Không thể đọc số liệu chatbot: {type(error).__name__}",
        }

    circuit_breakers = []
    for model in dict.fromkeys((settings.gemini_model, settings.gemini_fallback_model)):
        if not model:
            continue
        if not redis_is_available():
            circuit_breakers.append(get_local_circuit_status(model))
            continue
        try:
            is_open = bool(await redis.get(f"ai:circuit-open:{model}"))
            ttl_seconds = max(int(await redis.ttl(f"ai:circuit-open:{model}")), 0) if is_open else 0
            recent_failures = int(await redis.get(f"ai:model-failures:{model}") or 0)
            circuit_breakers.append(
                {
                    "model": model,
                    "open": is_open,
                    "ttl_seconds": ttl_seconds,
                    "recent_failures": recent_failures,
                }
            )
        except (RedisError, TypeError, ValueError):
            mark_redis_unavailable()
            circuit_breakers.append(get_local_circuit_status(model))

    return {
        "metrics": metrics,
        "circuit_breakers": circuit_breakers,
        "features": {
            "response_v2": settings.ai_response_v2_enabled,
            "chat_v2_percent": settings.ai_chat_v2_percent,
            "shadow_mode": settings.ai_shadow_mode_enabled,
            "router_v2": settings.ai_router_v2_enabled,
            "read_tools": settings.ai_read_tools_enabled,
            "model_routing": settings.ai_model_routing_enabled,
            "verifier": settings.ai_verifier_enabled,
            "pgvector_search_percent": settings.ai_pgvector_search_percent,
        },
    }
