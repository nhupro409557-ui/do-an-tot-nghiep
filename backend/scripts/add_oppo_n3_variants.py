import asyncio
import json
import sys
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import text
from app.infrastructure.database.session import AsyncSessionFactory

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionFactory() as session:
        # 1. Fetch product
        res = await session.execute(text("""
            SELECT id, name, sku, price, sale_price, stock_quantity
            FROM products 
            WHERE id = '5f0c3535-c5ce-4cac-8321-a32ac43aefd2';
        """))
        product = res.fetchone()
        if not product:
            print("Product OPPO Find N3 not found!")
            return
            
        p_id, p_name, p_sku, p_price, p_sale_price, p_stock = product
        print(f"Found product: {p_name} (ID: {p_id})")
        
        # Define colors and options
        colors = [
            {"code": "#1a1a1c", "name": "Đen"},
            {"code": "#e5c158", "name": "Vàng"}
        ]
        
        options = [
            {"name": "Màu sắc", "values": ["Đen", "Vàng"]},
            {"name": "Dung lượng", "values": ["512GB"]},
            {"name": "RAM", "values": ["16GB"]}
        ]
        
        # New default SKU
        default_sku = "OPPFN3-BK-512GB"
        now_utc = datetime.now(timezone.utc)
        
        # 2. Update product row
        await session.execute(text("""
            UPDATE products
            SET colors = :colors, options = :options, sku = :sku, updated_at = :now
            WHERE id = :id;
        """), {
            "colors": json.dumps(colors),
            "options": json.dumps(options),
            "sku": default_sku,
            "now": now_utc,
            "id": p_id
        })
        print("Product table colors, options, and SKU updated.")
        
        # 3. Create variants
        variants_to_add = [
            {
                "sku": "OPPFN3-BK-512GB",
                "color_name": "Đen",
                "color_code": "#1a1a1c",
                "storage": "512GB",
                "ram": "16GB",
                "price": 39990000.0,
                "sale_price": 34990000.0,
                "stock_quantity": 3,
                "is_default": True,
                "attributes": {"RAM": "16GB", "Màu sắc": "Đen", "Dung lượng": "512GB"}
            },
            {
                "sku": "OPPFN3-GD-512GB",
                "color_name": "Vàng",
                "color_code": "#e5c158",
                "storage": "512GB",
                "ram": "16GB",
                "price": 39990000.0,
                "sale_price": 34990000.0,
                "stock_quantity": 3,
                "is_default": False,
                "attributes": {"RAM": "16GB", "Màu sắc": "Vàng", "Dung lượng": "512GB"}
            }
        ]
        
        for nv in variants_to_add:
            nv_id = uuid4()
            await session.execute(text("""
                INSERT INTO product_variants (
                    id, product_id, sku, color_name, color_code, storage, ram, configuration, specs,
                    price, sale_price, compare_at_price, stock_quantity, is_active, is_default, status, attributes,
                    created_at, updated_at
                ) VALUES (
                    :id, :product_id, :sku, :color_name, :color_code, :storage, :ram, NULL, :attributes,
                    :price, :sale_price, NULL, :stock_quantity, TRUE, :is_default, 'active', :attributes,
                    :now, :now
                );
            """), {
                "id": nv_id,
                "product_id": p_id,
                "sku": nv["sku"],
                "color_name": nv["color_name"],
                "color_code": nv["color_code"],
                "storage": nv["storage"],
                "ram": nv["ram"],
                "price": nv["price"],
                "sale_price": nv["sale_price"],
                "stock_quantity": nv["stock_quantity"],
                "is_default": nv["is_default"],
                "attributes": json.dumps(nv["attributes"]),
                "now": now_utc
            })
            print(f"Created variant {nv['sku']} with ID: {nv_id}")
            
        await session.commit()
        print("Successfully added OPPO Find N3 variants.")

if __name__ == "__main__":
    asyncio.run(main())
