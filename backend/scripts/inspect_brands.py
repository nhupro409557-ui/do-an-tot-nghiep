import asyncio
from sqlalchemy import text
from app.infrastructure.database.session import AsyncSessionFactory

async def main():
    async with AsyncSessionFactory() as session:
        # Check active brands and their logos
        res = await session.execute(text("""
            SELECT id::text, code, name, logo_url
            FROM brands
            WHERE is_active = TRUE
            ORDER BY sort_order, name;
        """))
        brands = res.fetchall()
        print(f"Total active brands: {len(brands)}")
        for brand in brands[:10]:
            print(f"  Brand ID: {brand[0]} | Code: {brand[1]} | Name: {brand[2]} | Logo: {brand[3]}")

        # Check brand categories mappings
        res = await session.execute(text("""
            SELECT b.name, c.name, bc.category_id::text
            FROM brand_categories bc
            JOIN brands b ON b.id = bc.brand_id
            JOIN categories c ON c.id = bc.category_id;
        """))
        mappings = res.fetchall()
        print(f"\nBrand-Category mappings: {len(mappings)}")
        for m in mappings[:15]:
            print(f"  Brand: {m[0]} -> Category: {m[1]} (ID: {m[2]})")

if __name__ == "__main__":
    asyncio.run(main())
