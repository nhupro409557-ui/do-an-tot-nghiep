import asyncio
import uuid
import json
from fastapi import HTTPException
from sqlalchemy import text
from app.infrastructure.database.session import AsyncSessionFactory
from app.api.v1.routers.admin_inventory import adjust_product_inventory
from app.api.v1.routers.admin_schemas import InventoryAdjustmentPayload

async def test_inventory_adjustment():
    print("Starting Product Level Inventory Adjustment Test...")
    async with AsyncSessionFactory() as session:
        # 1. Tạo sản phẩm test đơn giản
        product_id = uuid.uuid4()
        variant_id = uuid.uuid4()
        product_name = f"Simple Test Phone {uuid.uuid4().hex[:4]}"
        product_sku = f"STP-{uuid.uuid4().hex[:4].upper()}"
        variant_sku = f"{product_sku}-01"
        
        await session.execute(
            text("""
                INSERT INTO products (id, name, slug, category, brand, price, stock_quantity, status, options, sku)
                VALUES (:id, :name, 'simple-test-phone', 'PHONE', 'Apple', 1000.0, 0, 'DRAFT', '[]'::jsonb, :sku)
            """),
            {"id": product_id, "name": product_name, "sku": product_sku}
        )
        
        # Tạo variant mặc định
        await session.execute(
            text("""
                INSERT INTO product_variants (id, product_id, sku, price, stock_quantity, is_default, status, attributes, is_active)
                VALUES (:id, :pid, :sku, 1000.0, 0, true, 'active', '{}'::jsonb, true)
            """),
            {"id": variant_id, "pid": product_id, "sku": variant_sku}
        )
        await session.commit()
        print(f"   Created test product with 1 default variant. Initial stock = 0.")

        try:
            # 2. Điều chỉnh tồn kho ở cấp sản phẩm (truyền variantId = None)
            payload = InventoryAdjustmentPayload(
                variantId=None,
                delta=15,
                transactionType="RECEIPT",
                referenceCode=f"REF-{uuid.uuid4().hex[:4].upper()}",
                reason="Nhập kho sản phẩm test đơn giản",
            )
            print("   Running adjust_product_inventory with variantId=None, delta=+15...")
            res = await adjust_product_inventory(product_id, payload, idempotency_key=None, session=session)
            print(f"   API Response: {res}")
            
            # 3. Truy vấn DB kiểm tra xem stock của variant và product có bằng 15 không
            prod_stock = (await session.execute(
                text("SELECT stock_quantity FROM products WHERE id = :id"),
                {"id": product_id}
            )).scalar()
            
            var_stock = (await session.execute(
                text("SELECT stock_quantity FROM product_variants WHERE id = :id"),
                {"id": variant_id}
            )).scalar()
            
            print(f"   After adjustment: Product Stock = {prod_stock}, Variant Stock = {var_stock}")
            
            if prod_stock == 15 and var_stock == 15:
                print("   [PASS] Inventory successfully adjusted on variant and synced to product!")
            else:
                print(f"   [FAIL] Expected both to be 15, got Prod={prod_stock}, Var={var_stock}")
                
        finally:
            # Cleanup
            await session.execute(text("DELETE FROM product_imeis WHERE product_id = :pid"), {"pid": product_id})
            await session.execute(text("DELETE FROM inventory_adjustment_logs WHERE product_id = :pid"), {"pid": product_id})
            await session.execute(text("DELETE FROM product_variants WHERE product_id = :pid"), {"pid": product_id})
            await session.execute(text("DELETE FROM products WHERE id = :pid"), {"pid": product_id})
            await session.commit()
            print("   Cleanup completed.")

if __name__ == "__main__":
    asyncio.run(test_inventory_adjustment())
