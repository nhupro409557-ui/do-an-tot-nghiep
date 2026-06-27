import asyncio
import json
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

# Định nghĩa các ID danh mục, danh mục con và hãng
CATEGORY_ID = "9c068948-d328-4b1c-8722-de50b1c25c64" # Phụ kiện công nghệ (accessories)

SUBCATEGORIES = {
    "cable-usbc": "f02ced98-7641-48d6-8f4b-3359f87eeec3",
    "adapter-multiport": "edb23d7f-ae09-47fb-874f-4cf33f2e2394"
}

BRANDS = {
    "Apple": "07d19f56-c05e-4211-bf3d-2375957dfff0",
    "Anker": "a0b065d6-4fbe-4b74-853f-acf69fedf95b",
    "Ugreen": "f1e37100-138f-4607-b25c-d42f419f412e"
}

PRODUCTS_TO_SEED = [
    {
        "sku": "UGR-USBC-240W",
        "name": "Cáp sạc Ugreen USB-C to USB-C 240W 2m (Hỗ trợ PD 3.1)",
        "brand": "Ugreen",
        "subcat": "cable-usbc",
        "price": 390000,
        "discountPrice": 290000,
        "description": "Cáp sạc nhanh Ugreen USB-C sang USB-C hỗ trợ công suất cực khủng lên tới 240W (48V/5A) nhờ chuẩn Power Delivery 3.1 mới nhất. Sạc siêu nhanh và an toàn cho tất cả các dòng laptop cao cấp hiện nay như MacBook Pro 16 inch, Dell XPS, HP Spectre, Lenovo ThinkPad. Dây cáp được bọc dù siêu bền chắc chống gãy gập.",
        "specs": {"Chiều dài": "2m", "Công suất hỗ trợ": "Tối đa 240W (PD 3.1)", "Chất liệu vỏ": "Nylon bọc dù cao cấp", "Tốc độ truyền dữ liệu": "480Mbps"},
        "variants": [
            {"color": "Xám Space", "suffix": "GR", "price": 390000, "discountPrice": 290000, "stock": 120},
            {"color": "Đen", "suffix": "BK", "price": 390000, "discountPrice": 290000, "stock": 100}
        ]
    },
    {
        "sku": "APL-MAGSAFE3",
        "name": "Cáp sạc Apple USB-C sang MagSafe 3 2m",
        "brand": "Apple",
        "subcat": "cable-usbc",
        "price": 1490000,
        "discountPrice": 1350000,
        "description": "Cáp sạc chính hãng Apple dài 2 mét có đầu nối MagSafe 3 từ tính, giúp dễ dàng dẫn đầu cắm vào cổng sạc của MacBook Pro/MacBook Air thế hệ mới. Đèn LED trên đầu cắm chuyển sang màu hổ phách khi pin đang sạc và màu xanh lục khi pin đã sạc đầy. Thiết kế bọc dù chắc chắn tăng độ bền lâu dài.",
        "specs": {"Chiều dài": "2m", "Kết nối": "USB-C sang MagSafe 3", "Hãng sản xuất": "Apple chính hãng", "Đèn LED chỉ báo": "Có (Hổ phách/Xanh lục)"},
        "variants": [
            {"color": "Bạc Silver", "suffix": "SL", "price": 1490000, "discountPrice": 1350000, "stock": 50},
            {"color": "Đen Midnight", "suffix": "MN", "price": 1490000, "discountPrice": 1350000, "stock": 40}
        ]
    },
    {
        "sku": "ANK-PR100W",
        "name": "Củ sạc nhanh Anker Prime 100W GaN 3 cổng",
        "brand": "Anker",
        "subcat": "adapter-multiport",
        "price": 1890000,
        "discountPrice": 1590000,
        "description": "Củ sạc nhanh cao cấp Anker Prime 100W tích hợp công nghệ GaN thế hệ mới, cho phép sạc đồng thời 3 thiết bị với 2 cổng USB-C và 1 cổng USB-A. Công suất sạc đơn tối đa lên tới 100W trên cổng USB-C, đủ để sạc nhanh cho các dòng MacBook Pro, Dell XPS, ThinkPad và các dòng laptop văn phòng/học tập khác.",
        "specs": {"Tổng công suất": "Tối đa 100W", "Số cổng": "3 (2x USB-C, 1x USB-A)", "Công nghệ": "GaNPrime & ActiveShield 2.0", "Trọng lượng": "180g"},
        "variants": [
            {"color": "Đen Midnight", "suffix": "BK", "price": 1890000, "discountPrice": 1590000, "stock": 80}
        ]
    },
    {
        "sku": "ANK-765-140W",
        "name": "Cáp sạc nhanh Anker 765 USB-C to USB-C 140W Nylon 1.8m",
        "brand": "Anker",
        "subcat": "cable-usbc",
        "price": 450000,
        "discountPrice": 350000,
        "description": "Cáp sạc nhanh siêu bền Anker 765 hỗ trợ sạc nhanh công suất lên tới 140W (PD 3.1) cho tất cả các dòng laptop và máy tính bảng hiện nay. Vỏ bọc dù nylon bện mật độ cao mang lại tuổi thọ uốn cong cực kỳ ấn tượng lên tới 35,000 lần.",
        "specs": {"Chiều dài": "1.8m", "Công suất hỗ trợ": "Tối đa 140W", "Chất liệu vỏ": "Nylon bện siêu bền", "Độ bền đầu cáp": "Chịu 35,000 lần uốn cong"},
        "variants": [
            {"color": "Đen", "suffix": "BK", "price": 450000, "discountPrice": 350000, "stock": 150}
        ]
    }
]

async def main():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        # Lấy ID của kho MAIN
        res_loc = await conn.execute(text("SELECT id FROM inventory_locations WHERE code = 'MAIN'"))
        location_id = res_loc.scalar()
        if not location_id:
            print("Error: Location MAIN not found!")
            return
        print(f"MAIN Location ID: {location_id}")

        # Lấy các attached services của phụ kiện laptop
        res_services = await conn.execute(
            text("SELECT id, code FROM attached_services WHERE is_active = TRUE AND code IN ('VIP-1D1-ACCESSORY-12M', 'S24-ACCESSORY-12M')")
        )
        services = res_services.fetchall()
        service_ids = [s.id for s in services]
        print(f"Loaded active attached services: {[s.code for s in services]}")

        for p_data in PRODUCTS_TO_SEED:
            brand_uuid = BRANDS.get(p_data["brand"])
            subcat_uuid = SUBCATEGORIES.get(p_data["subcat"]) if p_data["subcat"] else None
            
            product_uuid = uuid4()
            slug = p_data["sku"].lower()
            
            sales_config = {
                "attachedServices": [{"serviceId": str(s_id)} for s_id in service_ids]
            }

            # Build options JSON
            colors = [v["color"] for v in p_data["variants"]]
            options = []
            if len(colors) > 0 and colors[0] != "Đen":
                options = [
                    {
                        "key": "color",
                        "title": "Màu sắc",
                        "values": [{"value": c, "label": c} for c in colors]
                    }
                ]

            # 1. Insert product record
            await conn.execute(
                text("""
                    INSERT INTO products (
                        id, sku, name, slug, category, brand, category_id, subcategory_id, brand_id,
                        description, specifications, seo_metadata, sales_config, price, sale_price,
                        stock_quantity, status, is_featured, is_flash_sale, options, rating, review_count
                    ) VALUES (
                        :id, :sku, :name, :slug, 'accessories', :brand, :category_id, :subcategory_id, :brand_id,
                        :description, :specifications, :seo_metadata, :sales_config, :price, :sale_price,
                        :stock_quantity, 'ACTIVE', FALSE, FALSE, :options, NULL, 0
                    )
                """),
                {
                    "id": product_uuid,
                    "sku": p_data["sku"],
                    "name": p_data["name"],
                    "slug": slug,
                    "brand": p_data["brand"],
                    "category_id": CATEGORY_ID,
                    "subcategory_id": subcat_uuid,
                    "brand_id": brand_uuid,
                    "description": p_data["description"],
                    "specifications": json.dumps(p_data["specs"], ensure_ascii=False),
                    "seo_metadata": json.dumps({"title": p_data["name"], "description": p_data["description"][:150], "slug": slug}, ensure_ascii=False),
                    "sales_config": json.dumps(sales_config, ensure_ascii=False),
                    "price": p_data["price"],
                    "sale_price": p_data["discountPrice"],
                    "stock_quantity": sum(v["stock"] for v in p_data["variants"]),
                    "options": json.dumps(options, ensure_ascii=False)
                }
            )

            # 2. Insert variants and inventory
            is_first = True
            for var in p_data["variants"]:
                var_uuid = uuid4()
                var_sku = f"{p_data['sku']}-{var['suffix']}"
                
                await conn.execute(
                    text("""
                        INSERT INTO product_variants (
                            id, product_id, sku, price, sale_price, stock_quantity,
                            status, is_default, attributes, images, color_name, is_active
                        ) VALUES (
                            :id, :product_id, :sku, :price, :sale_price, :stock_quantity,
                            'active', :is_default, :attributes, '[]'::jsonb, :color_name, TRUE
                        )
                    """),
                    {
                        "id": var_uuid,
                        "product_id": product_uuid,
                        "sku": var_sku,
                        "price": var["price"],
                        "sale_price": var["discountPrice"],
                        "stock_quantity": var["stock"],
                        "is_default": is_first,
                        "attributes": json.dumps({"color": var["color"]}, ensure_ascii=False),
                        "color_name": var["color"]
                    }
                )

                # Insert inventory levels
                await conn.execute(
                    text("""
                        INSERT INTO inventory_levels (
                            product_id, variant_id, location_id, on_hand_quantity, reserved_quantity,
                            safety_stock_quantity, reorder_point_quantity, average_unit_cost, updated_at
                        ) VALUES (
                            NULL, :variant_id, :location_id, :stock_quantity, 0, 0, 0, 0, NOW()
                        )
                    """),
                    {
                        "variant_id": var_uuid,
                        "location_id": location_id,
                        "stock_quantity": var["stock"]
                    }
                )

                is_first = False

            # 3. Gán attached services cho bảng quan hệ
            for s_id in service_ids:
                await conn.execute(
                    text("""
                        INSERT INTO product_attached_services (product_id, service_id)
                        VALUES (:product_id, :service_id)
                    """),
                    {"product_id": product_uuid, "service_id": s_id}
                )

            print(f"Seeded SKU: {p_data['sku']} | Name: {p_data['name']}")

        print("\nSuccessfully seeded laptop accessories with variants and inventory.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
