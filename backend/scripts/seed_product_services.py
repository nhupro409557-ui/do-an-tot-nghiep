import asyncio
import json
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

# Bản đồ cấu hình dịch vụ phù hợp cho từng danh mục sản phẩm
CATEGORY_SERVICES = {
    "Điện thoại": [
        "VIP-1D1-MOBILE-12M",
        "S24-MOBILE-12M",
        "RVVN-MOBILE-12M",
        "SCREEN-PHONE-PREMIUM",
        "DATA-PHONE-FULL",
        "CLEAN-PHONE-TABLET"
    ],
    "Máy tính bảng": [
        "VIP-1D1-MOBILE-12M",
        "S24-MOBILE-12M",
        "RVVN-MOBILE-12M",
        "DATA-PHONE-FULL",
        "CLEAN-PHONE-TABLET"
    ],
    "Máy tính xách tay": [
        "VIP-1D1-LAPTOP-12M",
        "S24-LAPTOP-24M",
        "SETUP-LAPTOP-PRO",
        "INSTALL-SSD-RAM",
        "CLEAN-LAPTOP-PRO"
    ],
    "Phụ kiện công nghệ": [
        "VIP-1D1-ACCESSORY-12M",
        "S24-ACCESSORY-12M"
    ],
    "Đồng hồ thông minh": [
        "VIP-1D1-ACCESSORY-12M",
        "S24-ACCESSORY-12M"
    ],
    "Camera": [
        "VIP-1D1-ACCESSORY-12M",
        "S24-ACCESSORY-12M"
    ],
    "Máy ảnh": [
        "VIP-1D1-ACCESSORY-12M",
        "S24-ACCESSORY-12M"
    ]
}

async def main():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        # 1. Đọc các dịch vụ đi kèm đang hoạt động
        res_services = await conn.execute(
            text("SELECT id, code, name, service_type, attribute_group FROM attached_services WHERE is_active = TRUE")
        )
        services = res_services.fetchall()
        service_map = {s.code: (s.id, s.service_type, s.attribute_group) for s in services}
        print(f"Loaded {len(services)} active attached services.")

        # 2. Đọc tất cả các sản phẩm đang kinh doanh
        res_products = await conn.execute(
            text("""
                SELECT p.id, p.name, p.sku, p.sales_config, c.name as cat_name 
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.deleted_at IS NULL
            """)
        )
        products = res_products.fetchall()
        print(f"Loaded {len(products)} active products.")

        updated_count = 0

        # 3. Gán dịch vụ cho từng sản phẩm
        for product in products:
            cat_name = product.cat_name
            product_id = product.id
            sku = product.sku
            name = product.name
            current_sales_config = product.sales_config or {}

            # Xác định các code dịch vụ phù hợp
            service_codes = CATEGORY_SERVICES.get(cat_name)
            if not service_codes:
                # Fallback nếu danh mục lạ, thử map theo tivi hoặc bỏ qua
                if "tivi" in (cat_name or "").lower():
                    service_codes = ["VIP-1D1-TV-12M"]
                else:
                    print(f"Skipping SKU: {sku} | Cat: {cat_name} (No matching service config)")
                    continue

            selected_service_ids = []
            used_groups = set()

            for code in service_codes:
                if code not in service_map:
                    continue
                s_id, s_type, attr_group = service_map[code]
                
                # Áp dụng quy tắc unique cho attribute_group
                group_key = f"{s_type}:{attr_group or s_id}"
                if attr_group and group_key in used_groups:
                    continue
                
                used_groups.add(group_key)
                selected_service_ids.append(s_id)

            if not selected_service_ids:
                continue

            # a. Xóa các quan hệ cũ trong bảng product_attached_services
            await conn.execute(
                text("DELETE FROM product_attached_services WHERE product_id = :product_id"),
                {"product_id": product_id}
            )

            # b. Thêm các quan hệ mới
            for s_id in selected_service_ids:
                await conn.execute(
                    text("""
                        INSERT INTO product_attached_services (product_id, service_id)
                        VALUES (:product_id, :service_id)
                    """),
                    {"product_id": product_id, "service_id": s_id}
                )

            # c. Đồng bộ hóa trường sales_config của bảng products
            sales_config = dict(current_sales_config)
            sales_config["attachedServices"] = [{"serviceId": str(s_id)} for s_id in selected_service_ids]

            await conn.execute(
                text("""
                    UPDATE products 
                    SET sales_config = CAST(:sales_config AS jsonb), updated_at = NOW() 
                    WHERE id = :product_id
                """),
                {"product_id": product_id, "sales_config": json.dumps(sales_config, ensure_ascii=False)}
            )

            updated_count += 1
            print(f"Assigned {len(selected_service_ids)} services to SKU: {sku} | Name: {name[:30]}")

        print(f"\nSuccessfully seeded and synced attached services for {updated_count} products.")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
