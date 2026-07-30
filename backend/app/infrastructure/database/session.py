from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.infrastructure.database.naming import TEST_DATABASE_PREFIX, database_name


engine_options = {"pool_pre_ping": True}
if database_name(settings.database_url).startswith(TEST_DATABASE_PREFIX):
    engine_options["poolclass"] = NullPool

engine = create_async_engine(settings.database_url, **engine_options)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionFactory() as session:
        yield session
