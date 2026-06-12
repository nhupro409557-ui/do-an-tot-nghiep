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
        # 1. Fetch product S26U
        res = await session.execute(text("""
            SELECT id, name, sku, price, sale_price, stock_quantity
            FROM products WHERE sku = 'S26U';
        """))
        product = res.fetchone()
        if not product:
            print("Product Samsung Galaxy S26 Ultra not found!")
            return

        p_id, p_name, p_sku, p_price, p_sale_price, p_stock = product
        print(f"Found product: {p_name} (ID: {p_id})")

        # 2. Update product colors, options
        # Theo hình: Đen Classic, Tím Cobalt, Trắng Classic, Xanh Sky Blue
        colors = [
            {"code": "#2f3133", "name": "Đen Classic"},
            {"code": "#726b8e", "name": "Tím Cobalt"},
            {"code": "#f1f0ee", "name": "Trắng Classic"},
            {"code": "#87ceeb", "name": "Xanh Sky Blue"}
        ]

        options = [
            {"name": "Màu sắc", "values": ["Đen Classic", "Tím Cobalt", "Trắng Classic", "Xanh Sky Blue"]},
            {"name": "Dung lượng", "values": ["256GB", "512GB", "1TB"]},
            {"name": "RAM", "values": ["16GB", "12GB"]}
        ]

        now_utc = datetime.now(timezone.utc)

        # 4 màu × 3 dung lượng × 15 stock = 180
        await session.execute(text("""
            UPDATE products
            SET colors = :colors,
                options = :options,
                stock_quantity = 180,
                updated_at = :now
            WHERE id = :id;
        """), {
            "colors": json.dumps(colors),
            "options": json.dumps(options),
            "now": now_utc,
            "id": p_id
        })
        print("Product colors and options updated.")

        # 3. Rename existing variant colors
        rename_map = [
            {"old_name": "Đen Titan", "new_name": "Đen Classic", "new_code": "#2f3133"},
            {"old_name": "Trắng Titan", "new_name": "Trắng Classic", "new_code": "#f1f0ee"},
            {"old_name": "Xanh Thiên Thanh", "new_name": "Xanh Sky Blue", "new_code": "#87ceeb"},
        ]

        for rm in rename_map:
            # Update color_name and color_code
            await session.execute(text("""
                UPDATE product_variants
                SET color_name = :new_name,
                    color_code = :new_code,
                    updated_at = :now
                WHERE product_id = :pid
                  AND color_name = :old_name
                  AND deleted_at IS NULL;
            """), {
                "new_name": rm["new_name"],
                "new_code": rm["new_code"],
                "old_name": rm["old_name"],
                "pid": p_id,
                "now": now_utc
            })

            # Update attributes JSON
            res_vars = await session.execute(text("""
                SELECT id, attributes FROM product_variants
                WHERE product_id = :pid
                  AND color_name = :new_name
                  AND deleted_at IS NULL;
            """), {"pid": p_id, "new_name": rm["new_name"]})
            variants = res_vars.fetchall()

            for v in variants:
                v_id, v_attrs = v
                if v_attrs:
                    attrs = json.loads(v_attrs) if isinstance(v_attrs, str) else v_attrs
                    if attrs.get("Màu sắc") == rm["old_name"]:
                        attrs["Màu sắc"] = rm["new_name"]
                        await session.execute(text("""
                            UPDATE product_variants
                            SET attributes = :attrs, updated_at = :now
                            WHERE id = :vid;
                        """), {
                            "attrs": json.dumps(attrs),
                            "now": now_utc,
                            "vid": v_id
                        })
            print(f"  Renamed '{rm['old_name']}' → '{rm['new_name']}'")

        # 4. Add new Tím Cobalt variants (256GB, 512GB, 1TB)
        new_variants = [
            {
                "sku": "S26U-CV-256GB",
                "storage": "256GB",
                "ram": "12GB",
                "price": 33990000.0,
                "sale_price": 31990000.0,
                "stock": 15,
                "attributes": {"RAM": "12GB", "Màu sắc": "Tím Cobalt", "Dung lượng": "256GB"}
            },
            {
                "sku": "S26U-CV-512GB",
                "storage": "512GB",
                "ram": "12GB",
                "price": 37990000.0,
                "sale_price": 35990000.0,
                "stock": 15,
                "attributes": {"RAM": "12GB", "Màu sắc": "Tím Cobalt", "Dung lượng": "512GB"}
            },
            {
                "sku": "S26U-CV-1TB",
                "storage": "1TB",
                "ram": "16GB",
                "price": 44990000.0,
                "sale_price": 42990000.0,
                "stock": 15,
                "attributes": {"RAM": "16GB", "Màu sắc": "Tím Cobalt", "Dung lượng": "1TB"}
            }
        ]

        for nv in new_variants:
            res_exist = await session.execute(text("""
                SELECT id FROM product_variants
                WHERE sku = :sku AND deleted_at IS NULL;
            """), {"sku": nv["sku"]})
            exist = res_exist.fetchone()

            if exist:
                print(f"  Variant {nv['sku']} already exists, updating.")
                await session.execute(text("""
                    UPDATE product_variants
                    SET color_name = 'Tím Cobalt',
                        color_code = '#726b8e',
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
                        :id, :product_id, :sku, 'Tím Cobalt', '#726b8e', :storage, :ram,
                        :price, :sale_price, NULL, :stock,
                        TRUE, FALSE, 'active', :attrs,
                        :now, :now
                    );
                """), {
                    "id": new_id,
                    "product_id": p_id,
                    "sku": nv["sku"],
                    "storage": nv["storage"],
                    "ram": nv["ram"],
                    "price": nv["price"],
                    "sale_price": nv["sale_price"],
                    "stock": nv["stock"],
                    "attrs": json.dumps(nv["attributes"]),
                    "now": now_utc
                })
                print(f"  Created variant {nv['sku']} (ID: {new_id})")

        await session.commit()
        print("\nSuccessfully updated Samsung Galaxy S26 Ultra colors and variants.")

if __name__ == "__main__":
    asyncio.run(main())
