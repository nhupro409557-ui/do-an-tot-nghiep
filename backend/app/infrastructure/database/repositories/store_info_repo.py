from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models import StoreInfo


async def get_store_info(session: AsyncSession) -> StoreInfo | None:
    stmt = select(StoreInfo).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_store_info(session: AsyncSession, params: dict) -> int:
    params_cleaned = {k: v for k, v in params.items() if k in {
        "name", "hotline", "email", "address", "description", "lat", "lng"
    }}

    params_cleaned["updated_at"] = datetime.now(timezone.utc)
    
    stmt = (
        update(StoreInfo)
        .values(**params_cleaned)
    )
    result = await session.execute(stmt)
    return int(result.rowcount or 0)
