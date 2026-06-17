import asyncio
import os
import re
import asyncpg
from app.config import settings

SQL_FILES = [
    "init_database.sql",
    "036_inventory_settings_and_receipt_metadata.sql",
    "037_inventory_enterprise_foundation.sql",
    "038_review_management_upgrade.sql",
    "039_review_resilience_and_user_controls.sql",
    "040_catalog_inventory_services_foundation.sql",
    "041_product_favorites.sql",
    "042_staff_user_permissions.sql",
    "043_video_management_split.sql",
    "044_product_image_comments.sql",
    "045_product_analytics_events.sql",
    "046_product_flat_variants.sql",
    "047_enterprise_product_revision_merge.sql",
    "048_exclude_revision_variants_from_unique_sku.sql",
    "049_product_variant_images.sql",
    "050_product_favorite_events.sql",
    "051_flash_sales.sql",
    "052_remove_category_seo_metadata.sql",
    "053_remove_brand_seo_metadata.sql",
    "054_product_discontinued_status.sql",
    "055_product_inherited_visibility.sql",
    "056_suppliers.sql",
    "057_inventory_receipt_lifecycle.sql",
    "058_inventory_receipt_imei_workflow.sql",
    "059_inventory_imei_enterprise_statuses.sql",
    "060_product_serial_number_management.sql",
    "061_product_imei_primary.sql",
    "062_inventory_receipt_audit_actors.sql",
    "063_inventory_receipt_reversal.sql",
    "064_inventory_levels_moving_average_cost.sql",
    "065_inventory_identifier_edit_requests.sql",
    "066_inventory_stock_count_workflow.sql",
    "067_inventory_adjustment_approval_workflow.sql",
    "068_product_serial_number_product_scope_unique.sql",
]

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

    for filename in SQL_FILES:
        filepath = os.path.join(migrations_dir, filename)
        if not os.path.exists(filepath):
            print(f"Migration file not found: {filepath}")
            continue
        conn = await asyncpg.connect(db_url)
        try:
            try:
                await run_migration_file(conn, filepath)
            except Exception as e:
                print(f"Failed to apply migration file {filename}: {e}")
        finally:
            await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
