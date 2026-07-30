from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

@asynccontextmanager
async def transaction_scope(session: AsyncSession):
    try:
        yield
        await session.commit()
    except Exception:
        await session.rollback()
        raise
