import asyncio
import asyncpg
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    conn = await asyncpg.connect("postgresql://postgres:anhnhu057@localhost:5432/postgres")
    
    # 1. Fetch product ID and basic fields for HONOR X9d 5G (HN-X9D)
    p = await conn.fetchrow("SELECT id, name FROM products WHERE sku = 'HN-X9D';")
    if not p:
        print("Product HN-X9D not found!")
        await conn.close()
        return
        
    p_id = p['id']
    print(f"Found Product: {p['name']} (ID: {p_id})")
    
    # 2. Configure colors (Keep only Vàng Bình Minh and Đen Bóng Đêm, delete Nâu Đỏ and Xanh Rừng)
    new_colors = [
        {"code": "#1a1a1c", "name": "Đen Bóng Đêm"},
        {"code": "#d4af37", "name": "Vàng Bình Minh"}
    ]
    
    new_options = [
        {
            "name": "Màu sắc",
            "values": ["Vàng Bình Minh", "Đen Bóng Đêm"]
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
    
    # 3. Soft delete the variants corresponding to "Nâu Đỏ" and "Xanh Rừng"
    # and keep "Vàng Bình Minh" and "Đen Bóng Đêm" active.
    variants = await conn.fetch("""
        SELECT id, sku, color_name, storage
        FROM product_variants
        WHERE product_id = $1;
    """, p_id)
    
    print(f"Found {len(variants)} variants to process.")
    
    for v in variants:
        v_id = v['id']
        sku = v['sku']
        color = v['color_name']
        
        if color in ("Nâu Đỏ", "Xanh Rừng"):
            await conn.execute("""
                UPDATE product_variants
                SET is_active = FALSE,
                    status = 'deleted',
                    deleted_at = NOW(),
                    updated_at = NOW()
                WHERE id = $1;
            """, v_id)
            print(f"  - Soft-deleted variant SKU: {sku} | Color: {color}")
        else:
            await conn.execute("""
                UPDATE product_variants
                SET is_active = TRUE,
                    status = 'active',
                    deleted_at = NULL,
                    updated_at = NOW()
                WHERE id = $1;
            """, v_id)
            print(f"  - Activated/kept active variant SKU: {sku} | Color: {color}")
            
    print("HONOR X9d 5G color deletion completed successfully.")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
