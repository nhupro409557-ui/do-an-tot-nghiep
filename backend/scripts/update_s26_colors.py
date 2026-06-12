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
        # 1. Fetch product S26
        res = await session.execute(text("""
            SELECT id, name, sku, price, sale_price, stock_quantity
            FROM products
            WHERE sku = 'S26';
        """))
        product = res.fetchone()
        if not product:
            print("Product Samsung Galaxy S26 not found!")
            return

        p_id, p_name, p_sku, p_price, p_sale_price, p_stock = product
        print(f"Found product: {p_name} (ID: {p_id})")

        # 2. Update product colors, options
        # Theo hình: Đen Classic, Tím Cobalt, Xanh Sky Blue, Trắng Classic
        colors = [
            {"code": "#1a1a1a", "name": "Đen Classic"},
            {"code": "#726b8e", "name": "Tím Cobalt"},
            {"code": "#87ceeb", "name": "Xanh Sky Blue"},
            {"code": "#fdfdfd", "name": "Trắng Classic"}
        ]

        options = [
            {"name": "Màu sắc", "values": ["Đen Classic", "Tím Cobalt", "Xanh Sky Blue", "Trắng Classic"]},
            {"name": "Dung lượng", "values": ["256GB", "512GB"]},
            {"name": "RAM", "values": ["12GB"]}
        ]

        now_utc = datetime.now(timezone.utc)

        # 4 màu × 2 dung lượng × 20 stock = 160 stock
        await session.execute(text("""
            UPDATE products
            SET colors = :colors,
                options = :options,
                stock_quantity = 160,
                updated_at = :now
            WHERE id = :id;
        """), {
            "colors": json.dumps(colors),
            "options": json.dumps(options),
            "now": now_utc,
            "id": p_id
        })
        print("Product colors and options updated.")

        # 3. Update existing variant color names
        # Đen → Đen Classic (variants S26-BK-*)
        rename_map = [
            {"old_name": "Đen", "new_name": "Đen Classic", "sku_prefix": "S26-BK-"},
            {"old_name": "Trắng", "new_name": "Trắng Classic", "sku_prefix": "S26-WH-"},
        ]

        for rm in rename_map:
            # Update color_name in product_variants
            await session.execute(text("""
                UPDATE product_variants
                SET color_name = :new_name,
                    updated_at = :now
                WHERE product_id = :pid
                  AND color_name = :old_name
                  AND deleted_at IS NULL;
            """), {
                "new_name": rm["new_name"],
                "old_name": rm["old_name"],
                "pid": p_id,
                "now": now_utc
            })

            # Update attributes JSON: replace old color name with new one
            res_vars = await session.execute(text("""
                SELECT id, attributes FROM product_variants
                WHERE product_id = :pid
                  AND sku LIKE :prefix
                  AND deleted_at IS NULL;
            """), {"pid": p_id, "prefix": rm["sku_prefix"] + "%"})
            variants = res_vars.fetchall()

            for v in variants:
                v_id, v_attrs = v
                if v_attrs:
                    attrs = json.loads(v_attrs) if isinstance(v_attrs, str) else v_attrs
                    if attrs.get("Màu sắc") == rm["old_name"]:
                        attrs["Màu sắc"] = rm["new_name"]
                        await session.execute(text("""
                            UPDATE product_variants
                            SET attributes = :attrs,
                                updated_at = :now
                            WHERE id = :vid;
                        """), {
                            "attrs": json.dumps(attrs),
                            "now": now_utc,
                            "vid": v_id
                        })
            print(f"  Renamed '{rm['old_name']}' → '{rm['new_name']}' in variants.")

        # 4. Add new Xanh Sky Blue variants (256GB + 512GB)
        new_variants = [
            {
                "sku": "S26-SB-256GB",
                "color_name": "Xanh Sky Blue",
                "color_code": "#87ceeb",
                "storage": "256GB",
                "ram": "12GB",
                "price": 22990000.0,
                "sale_price": 21990000.0,
                "stock": 20,
                "is_default": False,
                "attributes": {"RAM": "12GB", "Màu sắc": "Xanh Sky Blue", "Dung lượng": "256GB"}
            },
            {
                "sku": "S26-SB-512GB",
                "color_name": "Xanh Sky Blue",
                "color_code": "#87ceeb",
                "storage": "512GB",
                "ram": "12GB",
                "price": 26990000.0,
                "sale_price": 25990000.0,
                "stock": 20,
                "is_default": False,
                "attributes": {"RAM": "12GB", "Màu sắc": "Xanh Sky Blue", "Dung lượng": "512GB"}
            }
        ]

        for nv in new_variants:
            # Check if variant exists
            res_exist = await session.execute(text("""
                SELECT id FROM product_variants
                WHERE sku = :sku AND deleted_at IS NULL;
            """), {"sku": nv["sku"]})
            exist = res_exist.fetchone()

            if exist:
                print(f"  Variant {nv['sku']} already exists, updating.")
                await session.execute(text("""
                    UPDATE product_variants
                    SET color_name = :color_name,
                        color_code = :color_code,
                        storage = :storage,
                        ram = :ram,
                        price = :price,
                        sale_price = :sale_price,
                        attributes = :attrs,
                        is_active = TRUE,
                        status = 'active',
                        updated_at = :now
                    WHERE sku = :sku AND deleted_at IS NULL;
                """), {
                    "color_name": nv["color_name"],
                    "color_code": nv["color_code"],
                    "storage": nv["storage"],
                    "ram": nv["ram"],
                    "price": nv["price"],
                    "sale_price": nv["sale_price"],
                    "attrs": json.dumps(nv["attributes"]),
                    "now": now_utc,
                    "sku": nv["sku"]
                })
            else:
                new_id = uuid4()
                await session.execute(text("""
                    INSERT INTO product_variants (
                        id, product_id, sku, color_name, color_code, storage, ram,
                        price, sale_price, compare_at_price, stock_quantity,
                        is_active, is_default, status, attributes,
                        created_at, updated_at
                    ) VALUES (
                        :id, :product_id, :sku, :color_name, :color_code, :storage, :ram,
                        :price, :sale_price, NULL, :stock,
                        TRUE, :is_default, 'active', :attrs,
                        :now, :now
                    );
                """), {
                    "id": new_id,
                    "product_id": p_id,
                    "sku": nv["sku"],
                    "color_name": nv["color_name"],
                    "color_code": nv["color_code"],
                    "storage": nv["storage"],
                    "ram": nv["ram"],
                    "price": nv["price"],
                    "sale_price": nv["sale_price"],
                    "stock": nv["stock"],
                    "is_default": nv["is_default"],
                    "attrs": json.dumps(nv["attributes"]),
                    "now": now_utc
                })
                print(f"  Created variant {nv['sku']} (ID: {new_id})")

        await session.commit()
        print("\nSuccessfully updated Samsung Galaxy S26 colors and variants.")

if __name__ == "__main__":
    asyncio.run(main())
