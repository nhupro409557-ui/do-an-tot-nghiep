import asyncio
import json
import sys
from sqlalchemy import text
from app.infrastructure.database.session import AsyncSessionFactory

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionFactory() as session:
        # Fetch variants
        res_vars = await session.execute(text("""
            SELECT id, sku, color_name, storage, ram, configuration, attributes
            FROM product_variants
            WHERE product_id = '182b69dd-0a83-409f-bde3-0d14461082ca';
        """))
        variants = res_vars.fetchall()
        
        print("\n--- ATTRIBUTES OF VARIANTS ---")
        for v in variants:
            v_dict = dict(v._mapping)
            print(f"SKU: {v_dict['sku']} | attributes: {v_dict['attributes']} (type: {type(v_dict['attributes'])})")

if __name__ == "__main__":
    asyncio.run(main())
