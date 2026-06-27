import asyncio
import json
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

# Định nghĩa các ID danh mục và danh mục con
CATEGORIES = {
    "cameras": "06104ed7-bc85-4bbe-a19f-b15b5a24ff96",
    "may-anh": "ba2c94b7-3db3-45a4-bdb9-c78df37bdab6",
    "accessories": "9c068948-d328-4b1c-8722-de50b1c25c64"
}

SUBCATEGORIES = {
    "security-camera": "c96e7416-ce2d-4215-95fc-d1a446117d8c",
    "camera-mirrorless": "185396b8-2f0c-45ad-a8bd-0bee966c5a6d",
    "camera-dslr": "e3c89309-7035-4384-9e85-2fbf8aff43d6",
    "adapter-gan": "5a4e4e5c-4315-416c-a87c-60f23204f6d2",
    "adapter-multiport": "edb23d7f-ae09-47fb-874f-4cf33f2e2394"
}

BRANDS = {
    "Ezviz": "2b48fe9c-ad64-472a-917f-4d4e3c32fc03",
    "Imou": "de3dfdbc-cf9a-4671-ae7a-1368a399131c",
    "Xiaomi": "34ef1ce1-1c44-4846-ae96-f0273277d594",
    "Sony": "d972caa4-c4d1-4ed6-964d-1c4cf612b7ec",
    "Canon": "402e96dd-df3f-4015-a335-07a2b9211792",
    "Fujifilm": "53edd425-cbe4-41e1-8b0f-b4633c7a3986",
    "Anker": "a0b065d6-4fbe-4b74-853f-acf69fedf95b",
    "Ugreen": "f1e37100-138f-4607-b25c-d42f419f412e",
    "Baseus": "c5303e8d-0ba5-43b5-8d9d-8f9d3f48b161"
}

PRODUCTS_TO_SEED = [
    # 1. Camera an ninh (cameras -> security-camera)
    {
        "sku": "EZV-C6N-2MP",
        "name": "Camera IP Wifi Ezviz C6N 1080p 2MP",
        "brand": "Ezviz",
        "cat": "cameras",
        "subcat": "security-camera",
        "price": 790000,
        "discountPrice": 590000,
        "description": "Camera IP Wifi Ezviz C6N 1080p được trang bị chức năng Smart IR, sử dụng ánh sáng hồng ngoại (IR) tiên tiến để thu được nhiều chi tiết hơn trong ánh sáng mờ. Với góc nhìn 360 độ và chức năng theo dõi thông minh, bạn sẽ không phải lo lắng về việc bỏ sót bất cứ điều gì.",
        "specs": {"Độ phân giải": "1080p (2.0 Megapixel)", "Góc nhìn": "Xoay ngang 340 độ, xoay dọc 55 độ", "Hồng ngoại": "Tối đa 10m", "Hỗ trợ thẻ nhớ": "MicroSD tối đa 256GB", "Đàm thoại": "2 chiều tích hợp"},
        "variants": [
            {"color": "Trắng", "suffix": "WH", "price": 790000, "discountPrice": 590000, "stock": 150}
        ]
    },
    {
        "sku": "IMO-B2C-2MP",
        "name": "Camera IP Wifi Ngoài Trời Imou Bullet 2C 1080p",
        "brand": "Imou",
        "cat": "cameras",
        "subcat": "security-camera",
        "price": 1190000,
        "discountPrice": 790000,
        "description": "Camera IP Wifi Ngoài Trời Imou Bullet 2C mang lại khả năng giám sát trực tiếp chất lượng Full HD 1080p với ống kính 2.8mm. Thiết bị hỗ trợ chuẩn nén H.265 giúp tiết kiệm đến 50% băng thông và dung lượng lưu trữ. Tính năng phát hiện con người bằng AI giúp bạn chỉ nhận được những cảnh báo thực sự quan trọng.",
        "specs": {"Độ phân giải": "1080p Full HD", "Chuẩn chống nước": "IP67 chịu mọi thời tiết", "Tầm nhìn đêm": "Hồng ngoại 30m", "Phát hiện chuyển động": "AI phát hiện người thông minh", "Kết nối": "Wi-Fi 2.4GHz & Cổng LAN"},
        "variants": [
            {"color": "Trắng", "suffix": "WH", "price": 1190000, "discountPrice": 790000, "stock": 120}
        ]
    },
    {
        "sku": "XIM-AW300",
        "name": "Camera an ninh ngoài trời xoay 360 Xiaomi AW300 2K",
        "brand": "Xiaomi",
        "cat": "cameras",
        "subcat": "security-camera",
        "price": 1290000,
        "discountPrice": 990000,
        "description": "Camera an ninh ngoài trời Xiaomi AW300 sở hữu độ phân giải 2K sắc nét, hỗ trợ ghi hình màu đầy đủ vào ban đêm nhờ đèn trợ sáng tích hợp. Khả năng chống nước chống bụi chuẩn IP66 bền bỉ, tích hợp còi báo động chủ động và đàm thoại hai chiều chất lượng cao.",
        "specs": {"Độ phân giải": "2K (2304 x 1296)", "Kháng nước": "Chuẩn IP66", "Tầm nhìn ban đêm": "Ghi hình màu (Full-color Night Vision)", "Cảnh báo": "Nhấp nháy đèn và còi báo động", "Góc nhìn ống kính": "101.7 độ"},
        "variants": [
            {"color": "Trắng", "suffix": "WH", "price": 1290000, "discountPrice": 990000, "stock": 100}
        ]
    },
    # 2. Máy ảnh (may-anh)
    {
        "sku": "SONY-A6400",
        "name": "Máy ảnh Mirrorless Sony Alpha A6400 (Kèm Lens 16-50mm)",
        "brand": "Sony",
        "cat": "may-anh",
        "subcat": "camera-mirrorless",
        "price": 23990000,
        "discountPrice": 20990000,
        "description": "Sony Alpha A6400 là chiếc máy ảnh mirrorless APS-C đa năng lý tưởng cho cả người chụp ảnh và quay vlog. Trang bị khả năng lấy nét tự động siêu nhanh 0.02 giây, tính năng Real-time Eye AF (lấy nét mắt thời gian thực) và quay video 4K HDR chất lượng cao.",
        "specs": {"Cảm biến": "24.2MP APS-C Exmor CMOS", "Bộ xử lý hình ảnh": "BIONZ X thế hệ mới", "Khả năng lấy nét": "425 điểm AF theo pha & tương phản", "Quay video": "4K UHD 30fps / Full HD 120fps", "Màn hình": "LCD 3.0 inch lật 180 độ cảm ứng"},
        "variants": [
            {"color": "Đen Classic", "suffix": "BK", "price": 23990000, "discountPrice": 20990000, "stock": 20},
            {"color": "Bạc Silver", "suffix": "SL", "price": 23990000, "discountPrice": 20990000, "stock": 15}
        ]
    },
    {
        "sku": "CANON-1500D",
        "name": "Máy ảnh DSLR Canon EOS 1500D (Kèm Lens 18-55mm IS II)",
        "brand": "Canon",
        "cat": "may-anh",
        "subcat": "camera-dslr",
        "price": 13490000,
        "discountPrice": 11490000,
        "description": "Máy ảnh DSLR Canon EOS 1500D là sự lựa chọn tuyệt vời cho người mới bắt đầu bước chân vào thế giới nhiếp ảnh chuyên nghiệp. Cảm biến 24.1 megapixel mang lại những bức ảnh chi tiết sắc nét và khả năng xóa phông tự nhiên tuyệt đẹp.",
        "specs": {"Cảm biến": "24.1 Megapixel APS-C CMOS", "Bộ xử lý": "DIGIC 4+", "Dải ISO": "100 - 6400 (Mở rộng đến 12800)", "Hệ thống lấy nét": "9 điểm AF", "Kết nối không dây": "Wi-Fi & NFC tích hợp"},
        "variants": [
            {"color": "Đen", "suffix": "BK", "price": 13490000, "discountPrice": 11490000, "stock": 35}
        ]
    },
    {
        "sku": "FUJI-XT30II",
        "name": "Máy ảnh Mirrorless Fujifilm X-T30 II (Chỉ Body)",
        "brand": "Fujifilm",
        "cat": "may-anh",
        "subcat": "camera-mirrorless",
        "price": 22990000,
        "discountPrice": 21490000,
        "description": "Fujifilm X-T30 II kết hợp kiểu dáng cổ điển hoài cổ với công nghệ kỹ thuật số hiện đại mạnh mẽ. Máy sở hữu cảm biến X-Trans CMOS 4 trứ danh cùng bộ xử lý hình ảnh tốc độ cao, hỗ trợ 18 chế độ giả lập màu phim nghệ thuật độc quyền của Fujifilm.",
        "specs": {"Cảm biến": "26.1 Megapixel X-Trans CMOS 4", "Bộ xử lý": "X-Processor 4", "Giả lập màu phim": "18 chế độ (Classic Chrome, Astia, Velvia...)", "Quay phim": "4K/30p & Full HD/240p", "Trọng lượng body": "378g (Đã gồm pin & thẻ)"},
        "variants": [
            {"color": "Đen Classic", "suffix": "BK", "price": 22990000, "discountPrice": 21490000, "stock": 15},
            {"color": "Bạc Carbon", "suffix": "SL", "price": 22990000, "discountPrice": 21490000, "stock": 10}
        ]
    },
    # 3. Phụ kiện công nghệ (accessories)
    {
        "sku": "ANK-PC10K",
        "name": "Sạc dự phòng Anker PowerCore Slim 10,000mAh PD 20W",
        "brand": "Anker",
        "cat": "accessories",
        "subcat": "adapter-gan",
        "price": 690000,
        "discountPrice": 520000,
        "description": "Sạc dự phòng siêu mỏng nhẹ Anker PowerCore Slim 10,000mAh hỗ trợ sạc nhanh chuẩn Power Delivery (PD) 20W chuyên dụng cho các dòng iPhone và thiết bị Android. Thiết kế vỏ nhám carbon chống xước và hạn chế trơn trượt tối ưu.",
        "specs": {"Dung lượng": "10,000 mAh / 37Wh", "Công suất ra": "Tối đa 20W PD USB-C", "Công nghệ sạc": "PowerIQ 3.0 & VoltageBoost", "Cổng kết nối": "1x USB-C (In/Out), 1x USB-A (Out)"},
        "variants": [
            {"color": "Đen Midnight", "suffix": "BK", "price": 690000, "discountPrice": 520000, "stock": 120},
            {"color": "Xanh Ocean", "suffix": "BL", "price": 690000, "discountPrice": 520000, "stock": 80}
        ]
    },
    {
        "sku": "UGR-HUB6IN1",
        "name": "Hub chuyển đổi đa năng Ugreen 6-in-1 USB-C sang HDMI 4K",
        "brand": "Ugreen",
        "cat": "accessories",
        "subcat": "adapter-multiport",
        "price": 550000,
        "discountPrice": 430000,
        "description": "Hub chuyển đổi đa năng Ugreen 6-trong-1 giải quyết triệt để tình trạng thiếu cổng kết nối trên các dòng MacBook, laptop mỏng nhẹ hiện nay. Hỗ trợ cổng xuất hình ảnh HDMI chuẩn 4K, 3 cổng USB 3.0 tốc độ cao và khe đọc thẻ nhớ SD/TF tiện dụng.",
        "specs": {"Đầu vào": "Cáp dẹt USB-C", "Cổng ra": "1x HDMI 4K@30Hz, 3x USB 3.0 (5Gbps), 1x SD Slot, 1x TF Slot", "Chất liệu": "Vỏ hợp kim nhôm tản nhiệt nguyên khối", "Khả năng tương thích": "macOS, Windows, iPadOS"},
        "variants": [
            {"color": "Xám Space", "suffix": "GR", "price": 550000, "discountPrice": 430000, "stock": 150}
        ]
    },
    {
        "sku": "BAS-GAN6-45W",
        "name": "Củ sạc nhanh Baseus GaN6 Pro 45W 2 cổng Type-C",
        "brand": "Baseus",
        "cat": "accessories",
        "subcat": "adapter-gan",
        "price": 490000,
        "discountPrice": 390000,
        "description": "Củ sạc nhanh Baseus GaN6 Pro 45W áp dụng công nghệ bán dẫn GaN thế hệ thứ 6 tiên tiến, mang lại hiệu suất sạc vượt trội và kích thước cực kỳ nhỏ gọn. Thiết kế 2 cổng USB-C hỗ trợ sạc nhanh đồng thời 2 thiết bị an toàn, không bị quá nhiệt nhờ công nghệ BCT.",
        "specs": {"Công suất tối đa": "45W", "Công nghệ": "GaN6 Pro & BCT", "Cổng kết nối": "2x USB-C", "Hỗ trợ chuẩn sạc": "PD 3.0, QC 4+, PPS, AFC"},
        "variants": [
            {"color": "Đen", "suffix": "BK", "price": 490000, "discountPrice": 390000, "stock": 180},
            {"color": "Trắng", "suffix": "WH", "price": 490000, "discountPrice": 390000, "stock": 120}
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

        # Lấy các attached services của phụ kiện/camera/máy ảnh (dùng chung VIP-1D1-ACCESSORY-12M, S24-ACCESSORY-12M)
        res_services = await conn.execute(
            text("SELECT id, code FROM attached_services WHERE is_active = TRUE AND code IN ('VIP-1D1-ACCESSORY-12M', 'S24-ACCESSORY-12M')")
        )
        services = res_services.fetchall()
        service_ids = [s.id for s in services]
        print(f"Loaded active attached services: {[s.code for s in services]}")

        for p_data in PRODUCTS_TO_SEED:
            brand_uuid = BRANDS.get(p_data["brand"])
            cat_uuid = CATEGORIES.get(p_data["cat"])
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
                        :id, :sku, :name, :slug, :category, :brand, :category_id, :subcategory_id, :brand_id,
                        :description, :specifications, :seo_metadata, :sales_config, :price, :sale_price,
                        :stock_quantity, 'ACTIVE', FALSE, FALSE, :options, NULL, 0
                    )
                """),
                {
                    "id": product_uuid,
                    "sku": p_data["sku"],
                    "name": p_data["name"],
                    "slug": slug,
                    "category": p_data["cat"],
                    "brand": p_data["brand"],
                    "category_id": cat_uuid,
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

        print("\nSuccessfully seeded new cameras, security cameras and accessories with variants and inventory.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
