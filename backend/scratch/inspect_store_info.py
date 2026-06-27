import asyncio
import asyncpg
from app.config import settings

async def main():
    db_url = settings.database_url
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    
    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch("SELECT * FROM store_info")
        print(f"Total rows in store_info: {len(rows)}")
        for r in rows:
            print(dict(r))
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
