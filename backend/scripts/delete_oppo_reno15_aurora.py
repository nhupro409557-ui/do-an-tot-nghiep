import asyncio
import json
import sys
from datetime import datetime, timezone
from sqlalchemy import text
from app.infrastructure.database.session import AsyncSessionFactory

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionFactory() as session:
        # 1. Fetch the OPPO Reno15 5G product
        res = await session.execute(text("""
            SELECT id, name, colors, options, sku
            FROM products 
            WHERE id = '1bcab5a6-c021-4976-83d8-6fd358a36192';
        """))
        product = res.fetchone()
        if not product:
            print("Product OPPO Reno15 5G not found!")
            return
            
        p_id, p_name, p_colors, p_options, p_sku = product
        print(f"Found product: {p_name} (ID: {p_id})")
        
        # 2. Update colors (remove "Xanh Cực Quang")
        original_colors = p_colors or []
        new_colors = [c for c in original_colors if c.get("name") != "Xanh Cực Quang"]
        print(f"Colors updated: {json.dumps(original_colors, ensure_ascii=False)} -> {json.dumps(new_colors, ensure_ascii=False)}")
        
        # 3. Update options (remove "Xanh Cực Quang" from "Màu sắc")
        original_options = p_options or []
        new_options = []
        for opt in original_options:
            if opt.get("name") == "Màu sắc":
                new_opt = {
                    "name": "Màu sắc",
                    "values": [val for val in opt.get("values", []) if val != "Xanh Cực Quang"]
                }
                new_options.append(new_opt)
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
        
        # 4. Soft-delete the variants corresponding to "Xanh Cực Quang"
        var_res = await session.execute(text("""
            SELECT id, sku, color_name, is_default, is_active
            FROM product_variants 
            WHERE product_id = :product_id;
        """), {"product_id": p_id})
        variants = var_res.fetchall()
        
        aurora_variant_ids = []
        active_other_variants = []
        
        for v in variants:
            v_id, v_sku, v_color, v_is_default, v_is_active = v
            if v_color == "Xanh Cực Quang":
                aurora_variant_ids.append(v_id)
            elif v_is_active:
                active_other_variants.append((v_id, v_sku, v_is_default))
                
        # Soft delete the Aurora variants
        now_utc = datetime.now(timezone.utc)
        for a_id in aurora_variant_ids:
            await session.execute(text("""
                UPDATE product_variants
                SET is_active = FALSE,
                    status = 'deleted',
                    is_default = FALSE,
                    deleted_at = :now,
                    updated_at = :now
                WHERE id = :id;
            """), {"now": now_utc, "id": a_id})
            print(f"Soft-deleted aurora variant ID: {a_id}")
            
        # 5. Check default variant constraint
        has_default = any(v[2] for v in active_other_variants)
        if not has_default and active_other_variants:
            # Set the first active variant as default (e.g. OP-RN15-DB-256GB)
            def_id, def_sku, _ = active_other_variants[0]
            await session.execute(text("""
                UPDATE product_variants
                SET is_default = TRUE, updated_at = :now
                WHERE id = :id;
            """), {"now": now_utc, "id": def_id})
            
            # Also update product SKU to match the default variant SKU
            await session.execute(text("""
                UPDATE products
                SET sku = :sku, updated_at = :now
                WHERE id = :id;
            """), {"sku": def_sku, "now": now_utc, "id": p_id})
            print(f"Set default variant to: {def_sku} (ID: {def_id}) and updated product SKU.")
            
        await session.commit()
        print("Successfully updated OPPO Reno15 5G variants.")

if __name__ == "__main__":
    asyncio.run(main())
