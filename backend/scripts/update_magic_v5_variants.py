import asyncio
import asyncpg
import json

async def main():
    conn = await asyncpg.connect("postgresql://postgres:anhnhu057@localhost:5432/postgres")
    
    # 1. Fetch the product ID and basic fields
    p = await conn.fetchrow("SELECT id, name FROM products WHERE sku = 'HN-MGV5';")
    if not p:
        print("Product HN-MGV5 not found!")
        await conn.close()
        return
    
    p_id = p['id']
    print(f"Found Product: {p['name']} (ID: {p_id})")
    
    # 2. Update product options
    new_options = [
        {
            "name": "Màu sắc",
            "values": ["Trắng Ngà", "Vàng Bình Minh"]
        },
        {
            "name": "Dung lượng",
            "values": ["512GB", "1TB"]
        },
        {
            "name": "RAM",
            "values": ["12GB", "16GB"]
        }
    ]
    
    await conn.execute("""
        UPDATE products
        SET options = $1, updated_at = NOW()
        WHERE id = $2;
    """, json.dumps(new_options), p_id)
    print("Updated product options successfully.")
    
    # 3. Fetch variants
    variants = await conn.fetch("""
        SELECT id, sku, color_name, storage
        FROM product_variants
        WHERE product_id = $1 AND deleted_at IS NULL;
    """, p_id)
    
    print(f"Found {len(variants)} active variants to update.")
    
    updated_variants_count = 0
    for v in variants:
        v_id = v['id']
        sku = v['sku']
        color = v['color_name']
        storage = v['storage']
        
        # Determine RAM based on storage capacity
        if storage == '512GB':
            ram_val = '12GB'
        elif storage == '1TB':
            ram_val = '16GB'
        else:
            # Fallback if storage value is not matching exactly
            ram_val = '12GB' if '512' in sku else '16GB' if '1T' in sku else '12GB'
            
        new_specs = {
            "storage": storage,
            "ram": ram_val
        }
        
        new_attributes = {
            "Màu sắc": color,
            "Dung lượng": storage,
            "RAM": ram_val
        }
        
        await conn.execute("""
            UPDATE product_variants
            SET ram = $1,
                specs = $2,
                attributes = $3,
                updated_at = NOW()
            WHERE id = $4;
        """, ram_val, json.dumps(new_specs), json.dumps(new_attributes), v_id)
        
        print(f"  - Updated variant SKU: {sku} | Set RAM to {ram_val} | Storage to {storage}")
        updated_variants_count += 1
        
    print(f"Successfully updated {updated_variants_count} variants of HONOR Magic V5.")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
