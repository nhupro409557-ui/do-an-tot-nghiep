import asyncio
import os
import re
import asyncpg
from app.config import settings

BASELINE_FILE = "init_database.sql"
MIGRATION_FILE_PATTERN = re.compile(r"^\d{3}_.+\.sql$")


def discover_sql_files(migrations_dir: str) -> list[str]:
    incremental_files = sorted(
        filename
        for filename in os.listdir(migrations_dir)
        if MIGRATION_FILE_PATTERN.match(filename)
    )
    return [BASELINE_FILE, *incremental_files]

def split_sql_statements(sql_text):
    statements = []
    current = []
    in_single_quote = False
    in_double_quote = False
    dollar_tag = None
    escape = False
    
    i = 0
    n = len(sql_text)
    while i < n:
        char = sql_text[i]
        if escape:
            current.append(char)
            escape = False
            i += 1
            continue
        
        if char == '\\' and dollar_tag is None:
            current.append(char)
            escape = True
            i += 1
            continue
            
        # Check for dollar quote start/end
        if char == '$' and not in_single_quote and not in_double_quote:
            match = re.match(r'^\$([a-zA-Z_0-9]*)\$', sql_text[i:])
            if match:
                tag = match.group(1)
                full_match = match.group(0)
                if dollar_tag is None:
                    dollar_tag = tag
                    current.append(full_match)
                    i += len(full_match)
                    continue
                elif tag == dollar_tag:
                    dollar_tag = None
                    current.append(full_match)
                    i += len(full_match)
                    continue
                    
        if dollar_tag is not None:
            current.append(char)
            i += 1
            continue
            
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            
        if char == ';' and not in_single_quote and not in_double_quote:
            statements.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        i += 1
        
    if current:
        tail = "".join(current).strip()
        if tail:
            statements.append(tail)
            
    return [s for s in statements if s]

async def run_migration_file(conn, filepath):
    print(f"Running migration file: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()
    
    statements = split_sql_statements(sql)
    print(f"Split into {len(statements)} statements.")
    
    for idx, stmt in enumerate(statements):
        try:
            await conn.execute(stmt)
        except asyncpg.exceptions.UniqueViolationError as e:
            # Safely ignore duplicate key/value violations for seed/migration resilience
            print(f"  [Warning] Statement {idx+1} skipped (UniqueViolationError): {e}")
        except Exception as e:
            print(f"  [Error] Statement {idx+1} failed: {repr(e)}")
            print(f"  Statement text: {stmt[:200]}...")
            raise e
            
    print(f"Finished: {filepath}")

async def main():
    migrations_dir = "migrations"
    db_url = settings.database_url
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    conn = await asyncpg.connect(db_url)
    try:
        database_initialized = await conn.fetchval("SELECT to_regclass('public.users') IS NOT NULL")
        if not database_initialized:
            await run_migration_file(conn, os.path.join(migrations_dir, BASELINE_FILE))
        else:
            print("Database baseline already exists; skipping init_database.sql.")

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            INSERT INTO schema_migrations (filename)
            VALUES ($1)
            ON CONFLICT (filename) DO NOTHING
            """,
            BASELINE_FILE,
        )

        applied_files = {
            row["filename"]
            for row in await conn.fetch("SELECT filename FROM schema_migrations")
        }
        for filename in discover_sql_files(migrations_dir)[1:]:
            if filename in applied_files:
                print(f"Migration already applied; skipping: {filename}")
                continue
            filepath = os.path.join(migrations_dir, filename)
            await run_migration_file(conn, filepath)
            await conn.execute(
                "INSERT INTO schema_migrations (filename) VALUES ($1)",
                filename,
            )
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
