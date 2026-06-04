import asyncio
import asyncpg
import json
import sys

# Reconfigure stdout to use utf-8 encoding to avoid Windows encoding issues
sys.stdout.reconfigure(encoding='utf-8')

async def main():
    conn = await asyncpg.connect("postgresql://postgres:anhnhu057@localhost:5432/postgres")
    
    # 1. Fetch the product ID and basic fields for HONOR 400 5G (HN-400)
    p = await conn.fetchrow("SELECT id, name FROM products WHERE sku = 'HN-400';")
    if not p:
        print("Product HN-400 not found!")
        await conn.close()
        return
    
    p_id = p['id']
    print(f"Found Product: {p['name']} (ID: {p_id})")
    
    # 2. Configure colors (Keep only Vàng Sa Mạc)
    new_colors = [
        {"code": "#e5d3b3", "name": "Vàng Sa Mạc"}
    ]
    
    # Configure options
    new_options = [
        {
            "name": "Màu sắc",
            "values": ["Vàng Sa Mạc"]
        },
        {
            "name": "Dung lượng",
            "values": ["256GB", "512GB"]
        },
        {
            "name": "RAM",
            "values": ["8GB", "12GB"]
        }
    ]
    
    await conn.execute("""
        UPDATE products
        SET colors = $1, options = $2, updated_at = NOW()
        WHERE id = $3;
    """, json.dumps(new_colors), json.dumps(new_options), p_id)
    print("Updated product colors and options successfully.")
    
    # 3. Fetch all variants (both active and soft-deleted) to update
    variants = await conn.fetch("""
        SELECT id, sku, color_name, storage
        FROM product_variants
        WHERE product_id = $1;
    """, p_id)
    
    print(f"Found {len(variants)} variants to process.")
    
    updated_variants_count = 0
    for v in variants:
        v_id = v['id']
        sku = v['sku']
        color = v['color_name']
        storage = v['storage']
        
        # Determine RAM based on storage capacity
        if storage == '256GB':
            ram_val = '8GB'
        elif storage == '512GB':
            ram_val = '12GB'
        else:
            ram_val = '8GB'
            
        new_specs = {
            "storage": storage,
            "ram": ram_val
        }
        
        new_attributes = {
            "Màu sắc": color,
            "Dung lượng": storage,
            "RAM": ram_val
        }
        
        # Determine if this color variant should be active or soft-deleted
        # Keep only "Vàng Sa Mạc", delete "Xám Mặt Trăng" and "Đen Bóng Đêm"
        if color == 'Vàng Sa Mạc':
            await conn.execute("""
                UPDATE product_variants
                SET ram = $1,
                    specs = $2,
                    attributes = $3,
                    is_active = TRUE,
                    status = 'active',
                    deleted_at = NULL,
                    updated_at = NOW()
                WHERE id = $4;
            """, ram_val, json.dumps(new_specs), json.dumps(new_attributes), v_id)
            print(f"  - Updated active variant SKU: {sku} | Set RAM to {ram_val} | Storage to {storage} | Color: {color}")
        else:
            # Soft delete variant
            await conn.execute("""
                UPDATE product_variants
                SET ram = $1,
                    specs = $2,
                    attributes = $3,
                    is_active = FALSE,
                    status = 'deleted',
                    deleted_at = NOW(),
                    updated_at = NOW()
                WHERE id = $4;
            """, ram_val, json.dumps(new_specs), json.dumps(new_attributes), v_id)
            print(f"  - Soft-deleted variant SKU: {sku} | Set RAM to {ram_val} | Storage to {storage} | Color: {color}")
            
        updated_variants_count += 1
        
    print(f"Successfully processed {updated_variants_count} variants of HONOR 400 5G.")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
