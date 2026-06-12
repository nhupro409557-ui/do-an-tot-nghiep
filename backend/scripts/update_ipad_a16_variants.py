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
        # 1. Fetch product IPADA16
        res = await session.execute(text("""
            SELECT id, name, sku, price, sale_price, stock_quantity
            FROM products
            WHERE sku = 'IPADA16' OR id = '19018a58-7514-44bf-b28f-65dd7482c358';
        """))
        product = res.fetchone()
        if not product:
            print("Product IPADA16 not found!")
            return

        p_id, p_name, p_sku, p_price, p_sale_price, p_stock = product
        print(f"Found product: {p_name} (ID: {p_id})")

        # 2. Define colors and configs
        colors = [
            {"code": "#d1d5db", "name": "Bạc"},
            {"code": "#f5e08c", "name": "Vàng"},
            {"code": "#e57c91", "name": "Hồng"},
            {"code": "#4b9cd3", "name": "Xanh"}
        ]

        configs = [
            {"name": "A16 Wifi 128GB", "code": "W128", "storage": "128GB", "price": 9290000.0},
            {"name": "A16 Wifi 256GB", "code": "W256", "storage": "256GB", "price": 11290000.0},
            {"name": "A16 5G 128GB",   "code": "5G128", "storage": "128GB", "price": 12290000.0},
            {"name": "A16 5G 256GB",   "code": "5G256", "storage": "256GB", "price": 14290000.0},
            {"name": "A16 Wifi 512GB", "code": "W512", "storage": "512GB", "price": 15290000.0}
        ]

        config_names = [c["name"] for c in configs]
        options = [
            {"name": "Màu sắc", "values": ["Bạc", "Vàng", "Hồng", "Xanh"]},
            {"name": "Phiên bản", "values": config_names}
        ]

        now_utc = datetime.now(timezone.utc)

        # Update product table
        # 20 variants * 10 stock = 200 stock
        await session.execute(text("""
            UPDATE products
            SET colors = :colors,
                options = :options,
                capacities = :capacities,
                price = 9290000.0,
                sale_price = 9290000.0,
                stock_quantity = 200,
                updated_at = :now
            WHERE id = :id;
        """), {
            "colors": json.dumps(colors),
            "options": json.dumps(options),
            "capacities": json.dumps(config_names),
            "now": now_utc,
            "id": p_id
        })
        print("Product table colors, options, capacities, price and stock updated.")

        # 3. Soft-delete existing variants
        res_del = await session.execute(text("""
            UPDATE product_variants
            SET deleted_at = :now,
                status = 'archived',
                is_default = FALSE,
                is_active = FALSE,
                updated_at = :now
            WHERE product_id = :product_id AND deleted_at IS NULL;
        """), {"product_id": p_id, "now": now_utc})
        print(f"Soft-deleted {res_del.rowcount} existing variants.")

        # 4. Insert 20 new variants
        for c in colors:
            color_suffix = ""
            if c["name"] == "Bạc":
                color_suffix = "SILVER"
            elif c["name"] == "Vàng":
                color_suffix = "YELLOW"
            elif c["name"] == "Hồng":
                color_suffix = "PINK"
            elif c["name"] == "Xanh":
                color_suffix = "BLUE"

            for conf in configs:
                variant_sku = f"IPADA16-{conf['code']}-{color_suffix}"
                is_default = (c["name"] == "Bạc" and conf["name"] == "A16 Wifi 128GB")

                specs_val = {
                    "configuration": conf["name"],
                    "storage": conf["storage"],
                    "ram": "6GB"
                }

                attributes_val = {
                    "Màu sắc": c["name"],
                    "Phiên bản": conf["name"]
                }

                # Check if variant already exists (active or deleted)
                res_exist = await session.execute(text("""
                    SELECT id FROM product_variants
                    WHERE sku = :sku;
                """), {"sku": variant_sku})
                exist = res_exist.fetchone()

                if exist:
                    print(f"  - Variant {variant_sku} exists. Reactivating and updating details.")
                    await session.execute(text("""
                        UPDATE product_variants
                        SET deleted_at = NULL,
                            price = :price,
                            sale_price = NULL,
                            color_name = :color_name,
                            color_code = :color_code,
                            storage = :storage,
                            ram = '6GB',
                            configuration = :config,
                            specs = :specs,
                            attributes = :attributes,
                            is_active = TRUE,
                            is_default = :is_default,
                            status = 'active',
                            updated_at = :now
                        WHERE sku = :sku;
                    """), {
                        "price": conf["price"],
                        "color_name": c["name"],
                        "color_code": c["code"],
                        "storage": conf["storage"],
                        "config": conf["name"],
                        "specs": json.dumps(specs_val),
                        "attributes": json.dumps(attributes_val),
                        "is_default": is_default,
                        "now": now_utc,
                        "sku": variant_sku
                    })
                else:
                    nv_id = uuid4()
                    await session.execute(text("""
                        INSERT INTO product_variants (
                            id, product_id, sku, color_name, color_code, storage, ram, configuration, specs,
                            price, sale_price, compare_at_price, stock_quantity, is_active, is_default, status, attributes,
                            created_at, updated_at
                        ) VALUES (
                            :id, :product_id, :sku, :color_name, :color_code, :storage, '6GB', :config, :specs,
                            :price, NULL, NULL, 10, TRUE, :is_default, 'active', :attributes,
                            :now, :now
                        );
                    """), {
                        "id": nv_id,
                        "product_id": p_id,
                        "sku": variant_sku,
                        "color_name": c["name"],
                        "color_code": c["code"],
                        "storage": conf["storage"],
                        "config": conf["name"],
                        "specs": json.dumps(specs_val),
                        "attributes": json.dumps(attributes_val),
                        "price": conf["price"],
                        "is_default": is_default,
                        "now": now_utc
                    })
                    print(f"  - Created variant {variant_sku} with ID: {nv_id}")

        await session.commit()
        print("Successfully updated iPad A16 Wifi options and variants.")

if __name__ == "__main__":
    asyncio.run(main())
