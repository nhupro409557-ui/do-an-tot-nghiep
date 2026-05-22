import asyncio
import os
from sqlalchemy import text
from app.infrastructure.database.session import AsyncSessionFactory
from app.config import settings

async def main():
    print("Database URL:", settings.database_url)
    async with AsyncSessionFactory() as session:
        # Check vouchers table columns
        res = await session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'vouchers';
        """))
        columns = res.fetchall()
        print("\nColumns in 'vouchers' table:")
        for col in columns:
            print(f"  {col[0]}: {col[1]}")

        # Check if total_budget_cap exists
        col_names = [col[0] for col in columns]
        if "total_budget_cap" not in col_names:
            print("\nMissing column: total_budget_cap")
        
        # Check security_audit_logs table columns
        res = await session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'security_audit_logs';
        """))
        audit_columns = res.fetchall()
        print("\nColumns in 'security_audit_logs' table:")
        for col in audit_columns:
            print(f"  {col[0]}: {col[1]}")

if __name__ == "__main__":
    asyncio.run(main())
