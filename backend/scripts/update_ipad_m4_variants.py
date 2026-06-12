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
        # 1. Fetch product IPADM4
        res = await session.execute(text("""
            SELECT id, name, sku, price, sale_price, stock_quantity
            FROM products
            WHERE sku = 'IPADM4';
        """))
        product = res.fetchone()
        if not product:
            print("Product IPADM4 not found!")
            return

        p_id, p_name, p_sku, p_price, p_sale_price, p_stock = product
        print(f"Found product: {p_name} (ID: {p_id})")

        # 2. Update product options to add connection type
        colors = [
            {"code": "#d1d5db", "name": "Bạc"},
            {"code": "#111827", "name": "Đen"}
        ]

        options = [
            {"name": "Màu sắc", "values": ["Bạc", "Đen"]},
            {"name": "Dung lượng", "values": ["256GB", "512GB", "1TB", "1TB Nano", "2TB", "2TB Nano"]},
            {"name": "Kết nối", "values": ["Wi-Fi", "Wi-Fi + Cellular"]}
        ]

        now_utc = datetime.now(timezone.utc)

        await session.execute(text("""
            UPDATE products
            SET colors = :colors, options = :options, updated_at = :now
            WHERE id = :id;
        """), {
            "colors": json.dumps(colors),
            "options": json.dumps(options),
            "now": now_utc,
            "id": p_id
        })
        print("Product table colors and options updated.")

        # 3. Update existing Wi-Fi variants
        res_vars = await session.execute(text("""
            SELECT id, sku, color_name, storage, ram
            FROM product_variants
            WHERE product_id = :product_id AND deleted_at IS NULL AND sku NOT LIKE '%-5G';
        """), {"product_id": p_id})
        old_variants = res_vars.fetchall()

        print(f"Updating {len(old_variants)} existing Wi-Fi variants...")
        for ov in old_variants:
            ov_id, ov_sku, ov_color, ov_storage, ov_ram = ov

            # Determine RAM if missing
            ram_val = ov_ram
            if not ram_val:
                ram_val = "16GB" if "1TB" in ov_storage or "2TB" in ov_storage else "8GB"

            new_specs = {
                "storage": ov_storage,
                "ram": ram_val,
                "configuration": "Wi-Fi"
            }

            new_attributes = {
                "RAM": ram_val,
                "Màu sắc": ov_color,
                "Dung lượng": ov_storage,
                "Kết nối": "Wi-Fi"
            }

            await session.execute(text("""
                UPDATE product_variants
                SET configuration = 'Wi-Fi',
                    ram = :ram,
                    specs = :specs,
                    attributes = :attributes,
                    updated_at = :now
                WHERE id = :id;
            """), {
                "ram": ram_val,
                "specs": json.dumps(new_specs),
                "attributes": json.dumps(new_attributes),
                "now": now_utc,
                "id": ov_id
            })
            print(f"  - Updated existing Wi-Fi variant: {ov_sku}")

        # 4. Insert new Wi-Fi + Cellular (5G) variants
        cellular_variants = [
            # 256GB - 8GB RAM
            {"sku": "IPADM4-256-SILVER-5G", "color_name": "Bạc", "color_code": "#d1d5db", "storage": "256GB", "ram": "8GB", "price": 34990000.0},
            {"sku": "IPADM4-256-BLACK-5G", "color_name": "Đen", "color_code": "#111827", "storage": "256GB", "ram": "8GB", "price": 34990000.0},
            # 512GB - 8GB RAM
            {"sku": "IPADM4-512-SILVER-5G", "color_name": "Bạc", "color_code": "#d1d5db", "storage": "512GB", "ram": "8GB", "price": 40990000.0},
            {"sku": "IPADM4-512-BLACK-5G", "color_name": "Đen", "color_code": "#111827", "storage": "512GB", "ram": "8GB", "price": 40990000.0},
            # 1TB - 16GB RAM
            {"sku": "IPADM4-1TB-SILVER-5G", "color_name": "Bạc", "color_code": "#d1d5db", "storage": "1TB", "ram": "16GB", "price": 51990000.0},
            {"sku": "IPADM4-1TB-BLACK-5G", "color_name": "Đen", "color_code": "#111827", "storage": "1TB", "ram": "16GB", "price": 51990000.0},
            # 1TB Nano - 16GB RAM
            {"sku": "IPADM4-1TBN-SILVER-5G", "color_name": "Bạc", "color_code": "#d1d5db", "storage": "1TB Nano", "ram": "16GB", "price": 54490000.0},
            {"sku": "IPADM4-1TBN-BLACK-5G", "color_name": "Đen", "color_code": "#111827", "storage": "1TB Nano", "ram": "16GB", "price": 54490000.0},
            # 2TB - 16GB RAM
            {"sku": "IPADM4-2TB-SILVER-5G", "color_name": "Bạc", "color_code": "#d1d5db", "storage": "2TB", "ram": "16GB", "price": 63490000.0},
            {"sku": "IPADM4-2TB-BLACK-5G", "color_name": "Đen", "color_code": "#111827", "storage": "2TB", "ram": "16GB", "price": 63490000.0},
            # 2TB Nano - 16GB RAM
            {"sku": "IPADM4-2TBN-SILVER-5G", "color_name": "Bạc", "color_code": "#d1d5db", "storage": "2TB Nano", "ram": "16GB", "price": 65990000.0},
            {"sku": "IPADM4-2TBN-BLACK-5G", "color_name": "Đen", "color_code": "#111827", "storage": "2TB Nano", "ram": "16GB", "price": 65990000.0},
        ]

        print("Inserting new Wi-Fi + Cellular variants...")
        for nv in cellular_variants:
            specs_val = {
                "storage": nv["storage"],
                "ram": nv["ram"],
                "configuration": "Wi-Fi + Cellular"
            }
            attributes_val = {
                "RAM": nv["ram"],
                "Màu sắc": nv["color_name"],
                "Dung lượng": nv["storage"],
                "Kết nối": "Wi-Fi + Cellular"
            }

            # Check if variant already exists (deleted_at is null)
            res_exist = await session.execute(text("""
                SELECT id FROM product_variants
                WHERE sku = :sku AND deleted_at IS NULL;
            """), {"sku": nv["sku"]})
            exist = res_exist.fetchone()

            if exist:
                print(f"  - Variant {nv['sku']} already exists. Updating price and active status.")
                await session.execute(text("""
                    UPDATE product_variants
                    SET price = :price,
                        sale_price = NULL,
                        color_name = :color_name,
                        color_code = :color_code,
                        storage = :storage,
                        ram = :ram,
                        configuration = 'Wi-Fi + Cellular',
                        specs = :specs,
                        attributes = :attributes,
                        is_active = TRUE,
                        status = 'active',
                        updated_at = :now
                    WHERE sku = :sku AND deleted_at IS NULL;
                """), {
                    "price": nv["price"],
                    "color_name": nv["color_name"],
                    "color_code": nv["color_code"],
                    "storage": nv["storage"],
                    "ram": nv["ram"],
                    "specs": json.dumps(specs_val),
                    "attributes": json.dumps(attributes_val),
                    "now": now_utc,
                    "sku": nv["sku"]
                })
            else:
                nv_id = uuid4()
                await session.execute(text("""
                    INSERT INTO product_variants (
                        id, product_id, sku, color_name, color_code, storage, ram, configuration, specs,
                        price, sale_price, compare_at_price, stock_quantity, is_active, is_default, status, attributes,
                        created_at, updated_at
                    ) VALUES (
                        :id, :product_id, :sku, :color_name, :color_code, :storage, :ram, 'Wi-Fi + Cellular', :specs,
                        :price, NULL, NULL, 10, TRUE, FALSE, 'active', :attributes,
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
                    "specs": json.dumps(specs_val),
                    "attributes": json.dumps(attributes_val),
                    "price": nv["price"],
                    "now": now_utc
                })
                print(f"  - Created variant {nv['sku']} with ID: {nv_id}")

        await session.commit()
        print("Successfully updated iPad Pro M4 11 inch options and variants.")

if __name__ == "__main__":
    asyncio.run(main())
