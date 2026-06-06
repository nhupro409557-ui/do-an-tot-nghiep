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
            SELECT id, name, colors, options, sku
            FROM products 
            WHERE id = '664a9354-89f1-4275-8a74-20ee67607d3f';
        """))
        product = res.fetchone()
        if not product:
            print("Product OPPO Reno15 F 5G not found!")
            return
            
        p_id, p_name, p_colors, p_options, p_sku = product
        print(f"Found product: {p_name} (ID: {p_id})")
        
        # 2. Update colors
        original_colors = p_colors or []
        # Remove "Xanh Cực Quang" and "Trắng Tinh Khôi"
        filtered_colors = [c for c in original_colors if c.get("name") not in ("Xanh Cực Quang", "Trắng Tinh Khôi")]
        # Add "Xanh Nhạt" and "Xanh Dương"
        new_colors = filtered_colors + [
            {"code": "#add8e6", "name": "Xanh Nhạt"},
            {"code": "#2196f3", "name": "Xanh Dương"}
        ]
        print(f"Colors updated: {json.dumps(original_colors, ensure_ascii=False)} -> {json.dumps(new_colors, ensure_ascii=False)}")
        
        # 3. Update options
        original_options = p_options or []
        new_options = []
        for opt in original_options:
            if opt.get("name") == "Màu sắc":
                # Filter old colors, add new colors
                filtered_vals = [val for val in opt.get("values", []) if val not in ("Xanh Cực Quang", "Trắng Tinh Khôi")]
                new_vals = filtered_vals + ["Xanh Nhạt", "Xanh Dương"]
                new_options.append({
                    "name": "Màu sắc",
                    "values": new_vals
                })
            else:
                new_options.append(opt)
        print(f"Options updated: {json.dumps(original_options, ensure_ascii=False)} -> {json.dumps(new_options, ensure_ascii=False)}")
        
        # Save product updates
        await session.execute(text("""
            UPDATE products
            SET colors = :colors, options = :options, updated_at = :now
            WHERE id = :id;
        """), {
            "colors": json.dumps(new_colors),
            "options": json.dumps(new_options),
            "now": datetime.now(timezone.utc),
            "id": p_id
        })
        print("Product table colors and options updated.")
        
        # 4. Soft-delete the variants corresponding to "Xanh Cực Quang" and "Trắng Tinh Khôi"
        var_res = await session.execute(text("""
            SELECT id, sku, color_name, is_default, is_active
            FROM product_variants 
            WHERE product_id = :product_id;
        """), {"product_id": p_id})
        variants = var_res.fetchall()
        
        variants_to_delete = []
        active_other_variants = []
        
        for v in variants:
            v_id, v_sku, v_color, v_is_default, v_is_active = v
            if v_color in ("Xanh Cực Quang", "Trắng Tinh Khôi"):
                variants_to_delete.append(v_id)
            elif v_is_active:
                active_other_variants.append((v_id, v_sku, v_is_default))
                
        # Soft delete
        now_utc = datetime.now(timezone.utc)
        for d_id in variants_to_delete:
            await session.execute(text("""
                UPDATE product_variants
                SET is_active = FALSE,
                    status = 'deleted',
                    is_default = FALSE,
                    deleted_at = :now,
                    updated_at = :now
                WHERE id = :id;
            """), {"now": now_utc, "id": d_id})
            print(f"Soft-deleted variant ID: {d_id}")
            
        # 5. Insert new variants
        new_variants_data = [
            # Xanh Nhạt
            {
                "sku": "OP-RN15F-LB-8-256",
                "color_name": "Xanh Nhạt",
                "color_code": "#add8e6",
                "storage": "256GB",
                "ram": "8GB",
                "price": 8490000.0,
                "sale_price": 7990000.0,
                "stock_quantity": 30,
                "attributes": {"RAM": "8GB", "Màu sắc": "Xanh Nhạt", "Dung lượng": "256GB"}
            },
            {
                "sku": "OP-RN15F-LB-12-256",
                "color_name": "Xanh Nhạt",
                "color_code": "#add8e6",
                "storage": "256GB",
                "ram": "12GB",
                "price": 9490000.0,
                "sale_price": 8990000.0,
                "stock_quantity": 30,
                "attributes": {"RAM": "12GB", "Màu sắc": "Xanh Nhạt", "Dung lượng": "256GB"}
            },
            # Xanh Dương
            {
                "sku": "OP-RN15F-B-8-256",
                "color_name": "Xanh Dương",
                "color_code": "#2196f3",
                "storage": "256GB",
                "ram": "8GB",
                "price": 8490000.0,
                "sale_price": 7990000.0,
                "stock_quantity": 30,
                "attributes": {"RAM": "8GB", "Màu sắc": "Xanh Dương", "Dung lượng": "256GB"}
            },
            {
                "sku": "OP-RN15F-B-12-256",
                "color_name": "Xanh Dương",
                "color_code": "#2196f3",
                "storage": "256GB",
                "ram": "12GB",
                "price": 9490000.0,
                "sale_price": 8990000.0,
                "stock_quantity": 30,
                "attributes": {"RAM": "12GB", "Màu sắc": "Xanh Dương", "Dung lượng": "256GB"}
            }
        ]
        
        for nv in new_variants_data:
            nv_id = uuid4()
            await session.execute(text("""
                INSERT INTO product_variants (
                    id, product_id, sku, color_name, color_code, storage, ram, configuration, specs,
                    price, sale_price, compare_at_price, stock_quantity, is_active, is_default, status, attributes,
                    created_at, updated_at
                ) VALUES (
                    :id, :product_id, :sku, :color_name, :color_code, :storage, :ram, NULL, :attributes,
                    :price, :sale_price, NULL, :stock_quantity, TRUE, FALSE, 'active', :attributes,
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
                "attributes": json.dumps(nv["attributes"]),
                "now": now_utc
            })
            print(f"Created variant {nv['sku']} with ID: {nv_id}")
            active_other_variants.append((nv_id, nv["sku"], False))
            
        # 6. Check default variant constraint
        has_default = any(v[2] for v in active_other_variants)
        if not has_default and active_other_variants:
            # We will make OP-RN15F-PK-8-256 (Pink, 8GB) default, let's find it or use active_other_variants[0]
            # Let's find OP-RN15F-PK-8-256
            default_candidate = None
            for v_id, v_sku, v_is_def in active_other_variants:
                if v_sku == "OP-RN15F-PK-8-256":
                    default_candidate = (v_id, v_sku)
                    break
            if not default_candidate:
                default_candidate = (active_other_variants[0][0], active_other_variants[0][1])
                
            def_id, def_sku = default_candidate
            
            await session.execute(text("""
                UPDATE product_variants
                SET is_default = TRUE, updated_at = :now
                WHERE id = :id;
            """), {"now": now_utc, "id": def_id})
            
            await session.execute(text("""
                UPDATE products
                SET sku = :sku, updated_at = :now
                WHERE id = :id;
            """), {"sku": def_sku, "now": now_utc, "id": p_id})
            print(f"Set default variant to: {def_sku} (ID: {def_id}) and updated product SKU.")
            
        await session.commit()
        print("Successfully updated OPPO Reno15 F 5G variants.")

if __name__ == "__main__":
    asyncio.run(main())
