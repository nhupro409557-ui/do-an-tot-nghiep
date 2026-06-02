import asyncio
import uuid
import json
from fastapi import HTTPException
from sqlalchemy import text
from app.infrastructure.database.session import AsyncSessionFactory
from app.api.v1.routers.admin_products import upsert_product_variants, delete_product_variant
from app.api.v1.routers.admin_schemas import ProductVariantPayload

async def clean_product(session, product_id):
    await session.execute(text("DELETE FROM product_variants WHERE product_id = :id"), {"id": product_id})
    await session.execute(text("DELETE FROM products WHERE id = :id"), {"id": product_id})
    await session.commit()

async def test_all_rules():
    print("Starting Product & Variant Rule Tests...")
    async with AsyncSessionFactory() as session:
        # Create a test product
        product_id = uuid.uuid4()
        product_name = f"Test Phone {uuid.uuid4().hex[:4]}"
        slug = f"test-phone-{uuid.uuid4().hex[:4]}"
        
        # Insert raw product
        await session.execute(
            text("""
                INSERT INTO products (id, name, slug, category, brand, price, stock_quantity, status, options)
                VALUES (:id, :name, :slug, 'PHONE', 'Apple', 1000.0, 0, 'DRAFT', :options)
            """),
            {
                "id": product_id,
                "name": product_name,
                "slug": slug,
                "options": json.dumps([
                    {"name": "Color", "values": ["Cam", "Trắng"]},
                    {"name": "Storage", "values": ["128GB", "256GB"]}
                ])
            }
        )
        await session.commit()
        print(f"Created test product: {product_name} ({product_id})")

        try:
            # 1. Test: Mismatched attributes (should fail)
            print("1. Testing mismatched attributes validation...")
            invalid_variants = [
                ProductVariantPayload(
                    sku=f"SKU-{uuid.uuid4().hex[:4].upper()}",
                    price=900.0,
                    stockQuantity=10,
                    attributes={"Color": "Đỏ", "Storage": "128GB"} # 'Đỏ' is not in options
                )
            ]
            try:
                await upsert_product_variants(session, product_id, invalid_variants, product_name)
                print("   [FAIL] Expected HTTPException for invalid Color attribute value")
            except HTTPException as e:
                print(f"   [PASS] Got expected error: {e.detail}")

            # 2. Test: Missing attributes (should fail)
            print("2. Testing missing attributes validation...")
            missing_attr_variants = [
                ProductVariantPayload(
                    sku=f"SKU-{uuid.uuid4().hex[:4].upper()}",
                    price=900.0,
                    stockQuantity=10,
                    attributes={"Color": "Cam"} # Missing 'Storage'
                )
            ]
            try:
                await upsert_product_variants(session, product_id, missing_attr_variants, product_name)
                print("   [FAIL] Expected HTTPException for missing Storage attribute")
            except HTTPException as e:
                print(f"   [PASS] Got expected error: {e.detail}")

            # 3. Test: Successful insertion of valid variants
            print("3. Testing successful insertion of valid variants...")
            sku1 = f"SKU-{uuid.uuid4().hex[:6].upper()}-A"
            sku2 = f"SKU-{uuid.uuid4().hex[:6].upper()}-B"
            valid_variants = [
                ProductVariantPayload(
                    sku=sku1,
                    price=1000.0,
                    stockQuantity=10,
                    isDefault=True,
                    isActive=True,
                    status="active",
                    attributes={"Color": "Cam", "Storage": "128GB"}
                ),
                ProductVariantPayload(
                    sku=sku2,
                    price=1200.0,
                    stockQuantity=5,
                    isDefault=False,
                    isActive=True,
                    status="active",
                    attributes={"Color": "Trắng", "Storage": "256GB"}
                )
            ]
            await upsert_product_variants(session, product_id, valid_variants, product_name)
            await session.commit()
            print("   [PASS] Successfully inserted variants.")

            # Verify in DB
            db_vars = (await session.execute(
                text("SELECT id, sku, is_default, attributes FROM product_variants WHERE product_id = :pid AND deleted_at IS NULL"),
                {"pid": product_id}
            )).mappings().all()
            print(f"   Fetched from DB: {len(db_vars)} active variants.")
            assert len(db_vars) == 2
            
            var_a = next(v for v in db_vars if v["sku"] == sku1)
            var_b = next(v for v in db_vars if v["sku"] == sku2)
            assert var_a["is_default"] is True
            assert var_b["is_default"] is False
            print("   [PASS] default flag correctly set in DB.")

            # 4. Test: Multiple default variants (should fail)
            print("4. Testing multiple default variants block...")
            multi_default_variants = [
                ProductVariantPayload(
                    id=var_a["id"],
                    sku=sku1,
                    price=1000.0,
                    isDefault=True,
                    attributes={"Color": "Cam", "Storage": "128GB"}
                ),
                ProductVariantPayload(
                    id=var_b["id"],
                    sku=sku2,
                    price=1200.0,
                    isDefault=True, # Multiple default
                    attributes={"Color": "Trắng", "Storage": "256GB"}
                )
            ]
            try:
                await upsert_product_variants(session, product_id, multi_default_variants, product_name)
                print("   [FAIL] Expected HTTPException for multiple default variants")
            except HTTPException as e:
                print(f"   [PASS] Got expected error: {e.detail}")

            # 5. Test: SKU Uniqueness constraint
            print("5. Testing active SKU duplicate prevention...")
            dup_sku = f"SKU-{uuid.uuid4().hex[:6].upper()}"
            # Create a second product
            product_id_2 = uuid.uuid4()
            await session.execute(
                text("""
                    INSERT INTO products (id, name, slug, category, brand, price, stock_quantity, status, options)
                    VALUES (:id, 'Second Phone', 'second-phone', 'PHONE', 'Apple', 1000.0, 0, 'DRAFT', '[]'::jsonb)
                """),
                {"id": product_id_2}
            )
            # Create variant for second product with dup_sku
            await session.execute(
                text("""
                    INSERT INTO product_variants (id, product_id, sku, price, stock_quantity, is_default, status, attributes)
                    VALUES (:id, :pid, :sku, 1000.0, 10, true, 'active', '{}'::jsonb)
                """),
                {"id": uuid.uuid4(), "pid": product_id_2, "sku": dup_sku}
            )
            await session.commit()

            # Now try to create a variant for product 1 with same dup_sku
            try:
                dup_payload = [
                    ProductVariantPayload(
                        id=var_a["id"],
                        sku=dup_sku, # Duplicate SKU
                        price=1000.0,
                        isDefault=True,
                        attributes={"Color": "Cam", "Storage": "128GB"}
                    )
                ]
                await upsert_product_variants(session, product_id, dup_payload, product_name)
                print("   [FAIL] Expected duplicate SKU warning")
            except HTTPException as e:
                print(f"   [PASS] Prevented duplicate active SKU. Error: {e.detail}")

            # 6. Test: Soft delete SKU reuse
            print("6. Testing SKU reuse after soft delete...")
            # Soft delete second product variant
            await session.execute(
                text("UPDATE product_variants SET deleted_at = NOW(), status = 'deleted' WHERE product_id = :pid"),
                {"pid": product_id_2}
            )
            await session.commit()
            # Now update product 1 variant to use dup_sku (should work now)
            try:
                reused_payload = [
                    ProductVariantPayload(
                        id=var_a["id"],
                        sku=dup_sku, # Reused SKU from soft-deleted variant
                        price=1000.0,
                        isDefault=True,
                        attributes={"Color": "Cam", "Storage": "128GB"}
                    ),
                    ProductVariantPayload(
                        id=var_b["id"],
                        sku=sku2,
                        price=1200.0,
                        isDefault=False,
                        attributes={"Color": "Trắng", "Storage": "256GB"}
                    )
                ]
                await upsert_product_variants(session, product_id, reused_payload, product_name)
                await session.commit()
                print("   [PASS] SKU successfully reused after soft delete.")
            except Exception as e:
                print(f"   [FAIL] Reusing soft-deleted SKU failed: {repr(e)}")

            # 7. Test: Last variant delete prevention
            print("7. Testing last variant delete protection...")
            # Try to delete variant B
            await delete_product_variant(product_id, var_b["id"], session)
            # Try to delete variant A (the last one)
            try:
                await delete_product_variant(product_id, var_a["id"], session)
                print("   [FAIL] Expected error trying to delete the last variant of a product")
            except HTTPException as e:
                print(f"   [PASS] Blocked deletion of the last variant. Error: {e.detail}")

            # Cleanup product 2
            await clean_product(session, product_id_2)

        finally:
            # Clean up product 1
            await clean_product(session, product_id)

    print("All backend tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_all_rules())
