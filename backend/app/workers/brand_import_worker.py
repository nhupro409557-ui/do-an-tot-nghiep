import asyncio
from uuid import UUID

from redis.asyncio import Redis

from app.application.brands.import_jobs import BRAND_IMPORT_QUEUE, process_brand_import_job
from app.config import settings
from app.infrastructure.database.session import AsyncSessionFactory


async def run_worker() -> None:
    redis_client = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    while True:
        _, job_id = await redis_client.blpop(BRAND_IMPORT_QUEUE)
        async with AsyncSessionFactory() as session:
            await process_brand_import_job(session, redis_client, UUID(str(job_id)))


if __name__ == "__main__":
    asyncio.run(run_worker())
