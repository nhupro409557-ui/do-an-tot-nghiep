import asyncio
from sqlalchemy import text
from app.infrastructure.database.session import AsyncSessionFactory

async def main():
    try:
        async with AsyncSessionFactory() as session:
            # Check product_variants table columns
            res = await session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'product_variants';
            """))
            variants_cols = res.fetchall()

            # Check products table columns
            res2 = await session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'products';
            """))
            products_cols = res2.fetchall()

            # Check indexes on product_variants
            res3 = await session.execute(text("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'product_variants';
            """))
            indexes = res3.fetchall()

        with open("verify_output_success.txt", "w", encoding="utf-8") as f:
            f.write("Columns in 'product_variants' table:\n")
            for col in variants_cols:
                f.write(f"  {col[0]}: {col[1]}\n")

            f.write("\nColumns in 'products' table:\n")
            for col in products_cols:
                f.write(f"  {col[0]}: {col[1]}\n")

            f.write("\nIndexes on 'product_variants' table:\n")
            for idx in indexes:
                f.write(f"  {idx[0]}: {idx[1]}\n")
            
            f.write("\nSUCCESS\n")
            
    except Exception as e:
        with open("verify_output_success.txt", "w", encoding="utf-8") as f:
            f.write(f"ERROR: {str(e)}\n")

if __name__ == "__main__":
    asyncio.run(main())
