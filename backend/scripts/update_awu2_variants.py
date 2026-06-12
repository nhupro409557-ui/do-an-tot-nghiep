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
        # 1. Fetch product AWU2
        res = await session.execute(text("""
            SELECT id, name, sku, price, sale_price, stock_quantity
            FROM products
            WHERE sku = 'AWU2' OR id = 'f902c67f-cc07-4d1f-82e0-4b2c60a52192';
        """))
        product = res.fetchone()
        if not product:
            print("Product AWU2 not found!")
            return

        p_id, p_name, p_sku, p_price, p_sale_price, p_stock = product
        print(f"Found product: {p_name} (ID: {p_id})")

        # 2. Update product options
        colors = [
            {"code": "#2a2b2d", "name": "Titan Đen"}
        ]

        strap_options = [
            "49mm Dây Alpine Size L",
            "49mm Dây Alpine Size S",
            "49mm Dây Trail Size S/M",
            "49mm Dây Cao Su",
            "49mm Dây Trail Size M/L",
            "49mm Dây Titan Size M",
            "49mm Dây Titan Size S",
            "49mm Dây Titan Size L",
            "49mm Dây Alpine Size M"
        ]

        options = [
            {"name": "Màu sắc", "values": ["Titan Đen"]},
            {"name": "Phiên bản", "values": strap_options}
        ]

        now_utc = datetime.now(timezone.utc)

        # 9 variants * 10 stock = 90 stock
        await session.execute(text("""
            UPDATE products
            SET colors = :colors,
                options = :options,
                capacities = :capacities,
                price = 16990000.0,
                sale_price = 16990000.0,
                stock_quantity = 90,
                updated_at = :now
            WHERE id = :id;
        """), {
            "colors": json.dumps(colors),
            "options": json.dumps(options),
            "capacities": json.dumps(strap_options),
            "now": now_utc,
            "id": p_id
        })
        print("Product table colors, options, capacities, price and stock updated.")

        # 3. Define variants
        variants_data = [
            {"sku": "AWU2-49-BLACK-ALPINEL", "strap": "Dây Alpine Size L", "config": "49mm Dây Alpine Size L", "is_default": False},
            {"sku": "AWU2-49-BLACK-ALPINES", "strap": "Dây Alpine Size S", "config": "49mm Dây Alpine Size S", "is_default": True}, # Mặc định
            {"sku": "AWU2-49-BLACK-TRAILSM", "strap": "Dây Trail Size S/M", "config": "49mm Dây Trail Size S/M", "is_default": False},
            {"sku": "AWU2-49-BLACK-CAOSU",   "strap": "Dây Cao Su",         "config": "49mm Dây Cao Su",         "is_default": False},
            {"sku": "AWU2-49-BLACK-TRAILML", "strap": "Dây Trail Size M/L", "config": "49mm Dây Trail Size M/L", "is_default": False},
            {"sku": "AWU2-49-BLACK-TITANM",  "strap": "Dây Titan Size M",   "config": "49mm Dây Titan Size M",   "is_default": False},
            {"sku": "AWU2-49-BLACK-TITANS",  "strap": "Dây Titan Size S",   "config": "49mm Dây Titan Size S",   "is_default": False},
            {"sku": "AWU2-49-BLACK-TITANL",  "strap": "Dây Titan Size L",   "config": "49mm Dây Titan Size L",   "is_default": False},
            {"sku": "AWU2-49-BLACK-ALPINEM", "strap": "Dây Alpine Size M",  "config": "49mm Dây Alpine Size M",  "is_default": False},
        ]

        print("Upserting product variants...")
        for vd in variants_data:
            specs_val = {
                "configuration": vd["config"],
                "case_size": "49mm",
                "strap": vd["strap"]
            }
            attributes_val = {
                "Màu sắc": "Titan Đen",
                "Phiên bản": vd["config"]
            }

            # Check if variant already exists
            res_exist = await session.execute(text("""
                SELECT id FROM product_variants
                WHERE sku = :sku AND deleted_at IS NULL;
            """), {"sku": vd["sku"]})
            exist = res_exist.fetchone()

            if exist:
                print(f"  - Variant {vd['sku']} already exists. Updating details.")
                await session.execute(text("""
                    UPDATE product_variants
                    SET price = 16990000.0,
                        sale_price = NULL,
                        color_name = 'Titan Đen',
                        color_code = '#2a2b2d',
                        storage = NULL,
                        ram = NULL,
                        configuration = :config,
                        specs = :specs,
                        attributes = :attributes,
                        is_active = TRUE,
                        is_default = :is_default,
                        status = 'active',
                        updated_at = :now
                    WHERE sku = :sku AND deleted_at IS NULL;
                """), {
                    "config": vd["config"],
                    "specs": json.dumps(specs_val),
                    "attributes": json.dumps(attributes_val),
                    "is_default": vd["is_default"],
                    "now": now_utc,
                    "sku": vd["sku"]
                })
            else:
                nv_id = uuid4()
                await session.execute(text("""
                    INSERT INTO product_variants (
                        id, product_id, sku, color_name, color_code, storage, ram, configuration, specs,
                        price, sale_price, compare_at_price, stock_quantity, is_active, is_default, status, attributes,
                        created_at, updated_at
                    ) VALUES (
                        :id, :product_id, :sku, 'Titan Đen', '#2a2b2d', NULL, NULL, :config, :specs,
                        16990000.0, NULL, NULL, 10, TRUE, :is_default, 'active', :attributes,
                        :now, :now
                    );
                """), {
                    "id": nv_id,
                    "product_id": p_id,
                    "sku": vd["sku"],
                    "config": vd["config"],
                    "specs": json.dumps(specs_val),
                    "attributes": json.dumps(attributes_val),
                    "is_default": vd["is_default"],
                    "now": now_utc
                })
                print(f"  - Created variant {vd['sku']} with ID: {nv_id}")

        await session.commit()
        print("Successfully updated Apple Watch Ultra 2 options and variants.")

if __name__ == "__main__":
    asyncio.run(main())
