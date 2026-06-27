import asyncio
import json
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

# Cấu hình danh mục và danh mục con
CATEGORIES = {
    "wearables": "d3088431-1e31-4ebe-a306-8da7e7b40972",
    "smartphones": "f757f4da-79b1-4888-91a1-c3b94c7a09c8",
    "tablets": "0e2b6e31-836e-44ee-962a-d408b4a1b4c0",
    "cameras": "06104ed7-bc85-4bbe-a19f-b15b5a24ff96"
}

SUBCATEGORIES = {
    "watch-sport": "595e6a06-0209-4ba7-bd8c-549a98fd5a3b",
    "watch-fashion": "0fac30b3-37ef-4ae8-b1f6-75634602e670",
    "smartband": "bd810ae0-1240-4591-b51f-38b14ab96d03",
    "phone-flagship": "af6096e0-b3ef-45f3-95e8-d628067c8595",
    "phone-midrange": "7330958f-fb4c-4524-a34b-83787297d616",
    "phone-budget": "b44d9bfa-dcfa-4390-8d81-abfff271c443",
    "phone-foldable": "17278c00-1b9b-4c6b-80ca-1f2cbbc00c9b",
    "tablet-pro": "519bce5e-9fd9-438d-a5f5-1ab0dfefde2e",
    "tablet-study": "db77b3b8-c12c-4412-8f33-48c6c0e44e24",
    "action-camera": "98d507f7-f475-45bb-b67f-ac504b197cc6",
    "security-camera": "c96e7416-ce2d-4215-95fc-d1a446117d8c"
}

BRANDS = {
    "Apple": "07d19f56-c05e-4211-bf3d-2375957dfff0",
    "Samsung": "88519edd-6175-4f8d-bee6-725bcfca9116",
    "Xiaomi": "34ef1ce1-1c44-4846-ae96-f0273277d594",
    "Garmin": "e3f0e6ca-abbf-4613-8c3b-2d50f954ef39",
    "GoPro": "d6b05db7-fbe0-4c87-baa7-57fa73df96d4",
    "DJI": "0bbe99f1-326a-4e03-a5fd-e895eaefe6b9",
    "Ezviz": "2b48fe9c-ad64-472a-917f-4d4e3c32fc03",
    "realme": "142196ce-84df-4d72-a008-9c44b82aae3e",
    "vivo": "416a6135-3542-4dc2-99c2-3dfde2618df5"
}

PRODUCTS_TO_SEED = [
    {
        "sku": "APL-WATCHS9",
        "name": "Đồng hồ thông minh Apple Watch Series 9",
        "brand": "Apple",
        "cat": "wearables",
        "subcat": "watch-fashion",
        "price": 10490000,
        "discountPrice": 9490000,
        "description": "Apple Watch Series 9 sở hữu con chip S9 SiP mạnh mẽ hơn bao giờ hết, màn hình Retina luôn bật siêu sáng lên đến 2000 nits và tính năng chạm đúp (Double Tap) vô cùng độc đáo. Đồng hồ tích hợp các tính năng theo dõi sức khỏe chuyên sâu như đo ECG, nồng độ oxy trong máu và phát hiện ngã.",
        "specs": {"Chip xử lý": "Apple S9 SiP", "Bộ nhớ": "64GB", "Độ sáng màn hình": "Lên tới 2000 nits", "Tính năng nổi bật": "Double Tap Gestures, Crash Detection"},
        "variants": [
            {"color": "Đen Midnight", "suffix": "MN", "price": 10490000, "discountPrice": 9490000, "stock": 40},
            {"color": "Bạc Silver", "suffix": "SL", "price": 10490000, "discountPrice": 9490000, "stock": 35}
        ]
    },
    {
        "sku": "GAR-FR965",
        "name": "Đồng hồ thể thao chuyên nghiệp Garmin Forerunner 965",
        "brand": "Garmin",
        "cat": "wearables",
        "subcat": "watch-sport",
        "price": 16490000,
        "discountPrice": 15290000,
        "description": "Garmin Forerunner 965 là mẫu đồng hồ chạy bộ và ba môn phối hợp cao cấp được trang bị màn hình cảm ứng AMOLED 1.4 inch sắc nét, viền titan sang trọng và hệ thống bản đồ màu tích hợp. Thiết bị cung cấp các chỉ số phân tích sức bền nâng cao như Trạng thái tập luyện, Động lực học chạy bộ và pin cơ thể.",
        "specs": {"Màn hình": "1.4 inch AMOLED cảm ứng", "Viền": "Titanium", "Thời lượng pin": "Đến 23 ngày (chế độ Smartwatch)", "Hệ thống định vị": "Đa tần số GNSS"},
        "variants": [
            {"color": "Đen Carbon", "suffix": "BK", "price": 16490000, "discountPrice": 15290000, "stock": 25},
            {"color": "Vàng Neon", "suffix": "YL", "price": 16490000, "discountPrice": 15290000, "stock": 15}
        ]
    },
    {
        "sku": "SAM-WATCH6C",
        "name": "Đồng hồ thông minh Samsung Galaxy Watch6 Classic 43mm",
        "brand": "Samsung",
        "cat": "wearables",
        "subcat": "watch-fashion",
        "price": 8990000,
        "discountPrice": 7490000,
        "description": "Galaxy Watch6 Classic đưa trở lại vòng xoay vật lý huyền thoại vô cùng tiện lợi cùng màn hình hiển thị lớn hơn 20%. Đồng hồ hỗ trợ phân tích thành phần cơ thể BIA, đo huyết áp, điện tâm đồ ECG và huấn luyện giấc ngủ chuyên sâu để bạn chăm sóc sức khỏe toàn diện.",
        "specs": {"Kích thước mặt": "43mm", "Vòng xoay": "Vật lý xoay xoay", "Chất liệu vỏ": "Thép không gỉ", "Hệ điều hành": "Wear OS Powered by Samsung"},
        "variants": [
            {"color": "Đen Classic", "suffix": "BK", "price": 8990000, "discountPrice": 7490000, "stock": 30},
            {"color": "Bạc Platinum", "suffix": "SL", "price": 8990000, "discountPrice": 7490000, "stock": 25}
        ]
    },
    {
        "sku": "XIM-WATCH4",
        "name": "Đồng hồ thông minh Xiaomi Redmi Watch 4",
        "brand": "Xiaomi",
        "cat": "wearables",
        "subcat": "watch-fashion",
        "price": 2690000,
        "discountPrice": 2390000,
        "description": "Redmi Watch 4 trang bị màn hình AMOLED kích thước lớn 1.97 inch sắc nét với tần số quét 60Hz mượt mà. Khung viền hợp kim nhôm sang trọng và núm xoay kim loại tiện dụng, hỗ trợ nghe gọi trực tiếp qua Bluetooth và thời lượng pin cực khủng lên đến 20 ngày.",
        "specs": {"Kích thước màn": "1.97 inch AMOLED 60Hz", "Chất liệu khung": "Hợp kim nhôm", "Thời lượng pin": "Đến 20 ngày", "Hỗ trợ cuộc gọi": "Bluetooth Call"},
        "variants": [
            {"color": "Đen Xám", "suffix": "BK", "price": 2690000, "discountPrice": 2390000, "stock": 60},
            {"color": "Bạc Ánh Trăng", "suffix": "SL", "price": 2690000, "discountPrice": 2390000, "stock": 50}
        ]
    },
    {
        "sku": "XIM-BAND8",
        "name": "Vòng đeo tay thông minh Xiaomi Smart Band 8",
        "brand": "Xiaomi",
        "cat": "wearables",
        "subcat": "smartband",
        "price": 990000,
        "discountPrice": 850000,
        "description": "Vòng đeo tay thông minh quốc dân Xiaomi Smart Band 8 mang đến sự nâng cấp vượt trội với màn hình AMOLED 1.62 inch hỗ trợ tần số quét 60Hz mượt mà và chế độ tự động điều chỉnh độ sáng. Hỗ trợ hơn 150 chế độ thể thao cùng dây đeo tháo nhanh thời trang tiện lợi.",
        "specs": {"Kích thước màn": "1.62 inch AMOLED 60Hz", "Tốc độ làm mới": "60Hz", "Số chế độ thể thao": "150+", "Thời lượng pin": "Lên tới 16 ngày"},
        "variants": [
            {"color": "Đen Graphite", "suffix": "BK", "price": 990000, "discountPrice": 850000, "stock": 150},
            {"color": "Vàng Champagne", "suffix": "GD", "price": 990000, "discountPrice": 850000, "stock": 120}
        ]
    },
    {
        "sku": "GOP-HERO12",
        "name": "Camera hành động GoPro Hero 12 Black",
        "brand": "GoPro",
        "cat": "cameras",
        "subcat": "action-camera",
        "price": 10990000,
        "discountPrice": 9990000,
        "description": "GoPro Hero 12 Black là dòng action camera tốt nhất cho giới sáng tạo nội dung với khả năng quay video chất lượng 5.3K sắc nét, hỗ trợ quay video dải động cao HDR cùng tính năng chống rung đỉnh cao HyperSmooth 6.0 đạt giải thưởng Emmy. Thời gian quay liên tục tăng gấp đôi nhờ hệ thống quản lý năng lượng tối ưu hóa.",
        "specs": {"Độ phân giải video": "5.3K60 / 4K120", "Chống rung": "HyperSmooth 6.0 + Horizon Lock", "Chống nước": "Độ sâu 10m không cần vỏ", "Dung lượng pin": "1720mAh Enduro"},
        "variants": [
            {"color": "Đen Classic", "suffix": "BK", "price": 10990000, "discountPrice": 9990000, "stock": 35}
        ]
    },
    {
        "sku": "DJI-ACTION4",
        "name": "Camera hành động DJI Osmo Action 4",
        "brand": "DJI",
        "cat": "cameras",
        "subcat": "action-camera",
        "price": 9190000,
        "discountPrice": 8290000,
        "description": "DJI Osmo Action 4 sở hữu cảm biến 1/1.3 inch siêu lớn mang lại chất lượng quay chụp thiếu sáng tuyệt vời, hỗ trợ màu sắc 10-bit D-Log M chuyên nghiệp. Thiết kế ngàm từ tính tháo lắp nhanh linh hoạt cùng hệ thống hai màn hình cảm ứng trước và sau vô cùng tiện lợi.",
        "specs": {"Kích thước cảm biến": "1/1.3-inch CMOS", "Độ phân giải": "4K/120fps", "Chống rung": "RockSteady 3.0+ / HorizonSteady", "Chống nước": "Sâu đến 18m"},
        "variants": [
            {"color": "Đen Standard", "suffix": "BK", "price": 9190000, "discountPrice": 8290000, "stock": 40}
        ]
    },
    {
        "sku": "EZV-H8C2K",
        "name": "Camera an ninh ngoài trời Ezviz H8c 2K 3MP",
        "brand": "Ezviz",
        "cat": "cameras",
        "subcat": "security-camera",
        "price": 1390000,
        "discountPrice": 1050000,
        "description": "Ezviz H8c 2K là giải pháp an ninh ngoài trời thông minh hỗ trợ xoay 360 độ linh hoạt, độ phân giải 2K 3MP sắc nét cùng thuật toán AI phát hiện người thông minh. Camera hỗ trợ ghi hình màu vào ban đêm (Color Night Vision) và còi hú chủ động phòng vệ răn đe.",
        "specs": {"Độ phân giải": "2K (2304 x 1296)", "Góc xoay ngang": "350 độ", "Góc xoay dọc": "80 độ", "Tầm nhìn ban đêm": "Hồng ngoại/Màu lên tới 30m"},
        "variants": [
            {"color": "Trắng", "suffix": "WH", "price": 1390000, "discountPrice": 1050000, "stock": 80}
        ]
    },
    {
        "sku": "XIM-PAD6PRO",
        "name": "Máy tính bảng Xiaomi Pad 6 Pro",
        "brand": "Xiaomi",
        "cat": "tablets",
        "subcat": "tablet-study",
        "price": 8990000,
        "discountPrice": 7990000,
        "description": "Xiaomi Pad 6 Pro sở hữu con chip Snapdragon 8+ Gen 1 cực kỳ mạnh mẽ, màn hình 11 inch tần số quét 144Hz WQHD+ siêu mượt mà cho trải nghiệm làm việc và giải trí đỉnh cao. Hệ thống 4 loa âm thanh nổi Dolby Atmos sống động cùng pin khủng 8600mAh sạc nhanh 67W.",
        "specs": {"Bộ xử lý": "Snapdragon 8+ Gen 1", "Màn hình": "11 inch 144Hz WQHD+", "Dung lượng pin": "8600mAh", "Sạc nhanh": "67W"},
        "variants": [
            {"color": "Xám Không Gian", "suffix": "GR", "price": 8990000, "discountPrice": 7990000, "stock": 50},
            {"color": "Xanh Dương Nhạt", "suffix": "BL", "price": 8990000, "discountPrice": 7990000, "stock": 40}
        ]
    },
    {
        "sku": "SAM-TABS9FE",
        "name": "Máy tính bảng Samsung Galaxy Tab S9 FE Wifi",
        "brand": "Samsung",
        "cat": "tablets",
        "subcat": "tablet-study",
        "price": 9990000,
        "discountPrice": 8690000,
        "description": "Samsung Galaxy Tab S9 FE Wifi được thiết kế bằng kim loại nguyên khối sang trọng, màn hình rộng 10.9 inch 90Hz mượt mà và khả năng chống nước, kháng bụi chuẩn IP68 hiếm hoi trên máy tính bảng. Tặng kèm bút S Pen đa năng trong hộp máy giúp bạn thỏa sức viết vẽ sáng tạo.",
        "specs": {"Màn hình": "10.9 inch 90Hz IPS", "Bộ xử lý": "Exynos 1380", "Bút S Pen": "Tích hợp sẵn (IP68)", "Chống nước": "Chuẩn IP68"},
        "variants": [
            {"color": "Xám Titan", "suffix": "GR", "price": 9990000, "discountPrice": 8690000, "stock": 45},
            {"color": "Xanh Mint", "suffix": "MN", "price": 9990000, "discountPrice": 8690000, "stock": 35}
        ]
    },
    {
        "sku": "APL-IPADAIRM2",
        "name": "Máy tính bảng iPad Air M2 11 inch 128GB Wifi",
        "brand": "Apple",
        "cat": "tablets",
        "subcat": "tablet-pro",
        "price": 16990000,
        "discountPrice": 15490000,
        "description": "iPad Air M2 11 inch mang đến hiệu năng vượt trội nhờ chip Apple M2 mạnh mẽ hơn 50% so với thế hệ trước. Màn hình Liquid Retina rực rỡ sắc nét, hỗ trợ Apple Pencil Pro thế hệ mới và thiết kế camera trước xoay ngang tiện lợi cho việc gọi video.",
        "specs": {"Chip xử lý": "Apple M2 (8 nhân CPU, 9 nhân GPU)", "Bộ nhớ trong": "128GB", "Màn hình": "11 inch Liquid Retina", "Kết nối": "Wi-Fi 6E"},
        "variants": [
            {"color": "Xám Không Gian", "suffix": "SG", "price": 16990000, "discountPrice": 15490000, "stock": 30},
            {"color": "Xanh Dương Cát", "suffix": "BL", "price": 16990000, "discountPrice": 15490000, "stock": 25},
            {"color": "Ánh Sao Starlight", "suffix": "SL", "price": 16990000, "discountPrice": 15490000, "stock": 20}
        ]
    },
    {
        "sku": "RME-C655G",
        "name": "Điện thoại realme C65 5G 6GB/128GB",
        "brand": "realme",
        "cat": "smartphones",
        "subcat": "phone-budget",
        "price": 4290000,
        "discountPrice": 3790000,
        "description": "realme C65 5G là mẫu điện thoại giá rẻ sở hữu thiết kế mỏng nhẹ hiện đại cùng hiệu năng ổn định từ chip Dimensity 6300 5G. Màn hình 120Hz mượt mà cùng camera AI 50MP sắc nét, hỗ trợ sạc nhanh 15W và pin lớn 5000mAh sử dụng bền bỉ.",
        "specs": {"Màn hình": "6.67 inch IPS 120Hz", "Chip xử lý": "MediaTek Dimensity 6300 5G", "RAM": "6GB", "Bộ nhớ": "128GB", "Dung lượng pin": "5000mAh"},
        "variants": [
            {"color": "Xanh Lục Bảo", "suffix": "GR", "price": 4290000, "discountPrice": 3790000, "stock": 90},
            {"color": "Đen Lông Vũ", "suffix": "BK", "price": 4290000, "discountPrice": 3790000, "stock": 80}
        ]
    },
    {
        "sku": "XIM-RN13P5G",
        "name": "Điện thoại Xiaomi Redmi Note 13 Pro 5G",
        "brand": "Xiaomi",
        "cat": "smartphones",
        "subcat": "phone-midrange",
        "price": 9490000,
        "discountPrice": 8290000,
        "description": "Xiaomi Redmi Note 13 Pro 5G nổi bật với camera chính siêu độ phân giải 200MP hỗ trợ chống rung quang học OIS cực kỳ sắc nét. Màn hình AMOLED 1.5K 120Hz viền siêu mỏng, chip Snapdragon 7s Gen 2 mượt mà và sạc nhanh Turbo 67W tiện lợi.",
        "specs": {"Camera chính": "200MP OIS", "Màn hình": "6.67 inch AMOLED 1.5K 120Hz", "Bộ xử lý": "Snapdragon 7s Gen 2 4nm", "Sạc nhanh": "67W Turbo Charge"},
        "variants": [
            {"color": "Đen Bán Dạ", "suffix": "BK", "price": 9490000, "discountPrice": 8290000, "stock": 70},
            {"color": "Xanh Đại Dương", "suffix": "BL", "price": 9490000, "discountPrice": 8290000, "stock": 60}
        ]
    },
    {
        "sku": "VIV-V30PRO",
        "name": "Điện thoại vivo V30 Pro 5G",
        "brand": "vivo",
        "cat": "smartphones",
        "subcat": "phone-midrange",
        "price": 14990000,
        "discountPrice": 12990000,
        "description": "vivo V30 Pro 5G được thiết kế siêu mỏng thời trang tích hợp vòng sáng Aura 3.0 chuyên nghiệp giúp chụp ảnh chân dung studio độc đáo. Hỗ trợ hệ thống 3 camera 50MP tinh chỉnh bởi hãng ống kính Zeiss lừng danh, mang đến chất lượng nhiếp ảnh di động đỉnh cao.",
        "specs": {"Hệ thống ống kính": "Co-engineered với ZEISS", "Camera trước/sau": "Đồng bộ 50MP", "Độ dày thân máy": "7.45mm siêu mỏng", "Chip xử lý": "Dimensity 8200 4nm"},
        "variants": [
            {"color": "Đen Classic", "suffix": "BK", "price": 14990000, "discountPrice": 12990000, "stock": 45},
            {"color": "Xanh Sóng Biển", "suffix": "BL", "price": 14990000, "discountPrice": 12990000, "stock": 40}
        ]
    },
    {
        "sku": "SAM-ZFLIP5",
        "name": "Điện thoại gập Samsung Galaxy Z Flip5 256GB",
        "brand": "Samsung",
        "cat": "smartphones",
        "subcat": "phone-foldable",
        "price": 25990000,
        "discountPrice": 16990000,
        "description": "Samsung Galaxy Z Flip5 sở hữu cơ chế bản lề Flex khít không khe hở vô cùng tinh xảo cùng màn hình ngoài Flex Window 3.4 inch độc đáo lớn gấp 3.7 lần thế hệ cũ. Cho phép bạn chạy trực tiếp các app, nhắn tin và chụp ảnh selfie chất lượng cao từ camera sau dễ dàng.",
        "specs": {"Màn hình ngoài": "3.4 inch Super AMOLED", "Màn hình trong": "6.7 inch Dynamic AMOLED 2X 120Hz", "Bản lề": "Flex Hinge không khe hở", "Chip xử lý": "Snapdragon 8 Gen 2 for Galaxy"},
        "variants": [
            {"color": "Xanh Mint", "suffix": "MN", "price": 25990000, "discountPrice": 16990000, "stock": 35},
            {"color": "Xám Phantom", "suffix": "GY", "price": 25990000, "discountPrice": 16990000, "stock": 25},
            {"color": "Tím Lavender", "suffix": "LV", "price": 25990000, "discountPrice": 16990000, "stock": 20}
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

        # Lấy tất cả các attached services đang hoạt động để phân loại gán sau
        res_services = await conn.execute(
            text("SELECT id, code, service_type, attribute_group FROM attached_services WHERE is_active = TRUE")
        )
        services = res_services.fetchall()
        service_map = {s.code: (s.id, s.service_type, s.attribute_group) for s in services}
        print(f"Loaded {len(services)} active attached services.")

        # Các nhóm dịch vụ chuẩn để gán
        mobile_services_codes = [
            "VIP-1D1-MOBILE-12M",
            "S24-MOBILE-12M",
            "RVVN-MOBILE-12M",
            "SCREEN-PHONE-PREMIUM",
            "DATA-PHONE-FULL",
            "CLEAN-PHONE-TABLET"
        ]
        
        accessory_services_codes = [
            "VIP-1D1-ACCESSORY-12M",
            "S24-ACCESSORY-12M"
        ]

        for p_data in PRODUCTS_TO_SEED:
            brand_uuid = BRANDS.get(p_data["brand"])
            cat_uuid = CATEGORIES.get(p_data["cat"])
            subcat_uuid = SUBCATEGORIES.get(p_data["subcat"]) if p_data["subcat"] else None
            
            product_uuid = uuid4()
            slug = p_data["sku"].lower()
            
            # Chọn các service phù hợp theo danh mục
            is_mobile = p_data["cat"] in ["smartphones", "tablets"]
            target_service_codes = mobile_services_codes if is_mobile else accessory_services_codes
            
            selected_service_ids = []
            used_groups = set()

            for code in target_service_codes:
                if code not in service_map:
                    continue
                s_id, s_type, attr_group = service_map[code]
                
                # Áp dụng quy tắc unique cho attribute_group
                group_key = f"{s_type}:{attr_group or s_id}"
                if attr_group and group_key in used_groups:
                    continue
                
                used_groups.add(group_key)
                selected_service_ids.append(s_id)

            sales_config = {
                "attachedServices": [{"serviceId": str(s_id)} for s_id in selected_service_ids]
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

            # 3. Gán attached services cho bảng quan hệ product_attached_services
            for s_id in selected_service_ids:
                await conn.execute(
                    text("""
                        INSERT INTO product_attached_services (product_id, service_id)
                        VALUES (:product_id, :service_id)
                    """),
                    {"product_id": product_uuid, "service_id": s_id}
                )

            print(f"Seeded SKU: {p_data['sku']} | Name: {p_data['name']}")

        print("\nSuccessfully seeded 15 more diverse products with variants and inventory.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
