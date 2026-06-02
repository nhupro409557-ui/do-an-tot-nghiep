import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://postgres:anhnhu057@localhost:5432/postgres')
    rows = await conn.fetch("""
        SELECT COUNT(*), brand, brand_id IS NULL AS brand_id_null, category, category_id IS NULL AS category_id_null 
        FROM products 
        GROUP BY brand, brand_id IS NULL, category, category_id IS NULL
    """)
    for r in rows:
        print(dict(r))
    await conn.close()

if __name__ == '__main__':
    asyncio.run(run())
