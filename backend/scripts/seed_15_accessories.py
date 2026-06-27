import asyncio
import json
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

# Thông số danh mục Phụ kiện công nghệ và các Danh mục con
CATEGORY_ID = "9c068948-d328-4b1c-8722-de50b1c25c64"
SUBCATEGORIES = {
    "cable-lightning": "52e3c085-8172-4b05-ae48-4c7350334adc",
    "audio-tws": "efebdaf0-d189-4704-ae3b-b0d6fe5a222a",
    "audio-overear": "743b07cb-6fce-41c4-b7d7-fd5be5b42711",
    "audio-sport": "1bf7bb3a-2b26-4638-b7f4-f6726797a310",
    "audio-gaming": "9f8fd614-89bd-4318-a9a5-b44aaa0eac3f",
    "adapter-gan": "5a4e4e5c-4315-416c-a87c-60f23204f6d2",
    "adapter-multiport": "edb23d7f-ae09-47fb-874f-4cf33f2e2394",
    "cable-usbc": "f02ced98-7641-48d6-8f4b-3359f87eeec3",
    "adapter-wireless": "1496573b-05e9-4dd3-bfaf-17d23cb96050",
    "cable-thunderbolt": "53dd057a-8016-4499-9579-a50fdd3c7330"
}

# Thương hiệu
BRANDS = {
    "Anker": "a0b065d6-4fbe-4b74-853f-acf69fedf95b",
    "Ugreen": "f1e37100-138f-4607-b25c-d42f419f412e",
    "Belkin": "eef94fe5-29e7-49f3-ad4b-7dfbf225969f",
    "Mophie": "352ae647-e031-45d0-9448-221ebd88a764",
    "Apple": "07d19f56-c05e-4211-bf3d-2375957dfff0",
    "JBL": "ccbb4035-219b-444f-8d87-44862a4e9dc4",
    "Sony": "d972caa4-c4d1-4ed6-964d-1c4cf612b7ec",
    "Razer": "5afd65aa-3d0d-49a1-b34d-af7ef2248cd1",
    "Marshall": "64cfd37e-b7a6-4a4e-af0b-3d80ec9ea335"
}

PRODUCTS_TO_SEED = [
    {
        "sku": "ANK-N65W",
        "name": "Củ sạc nhanh Anker Nano II 65W GaN",
        "brand": "Anker",
        "subcat": "adapter-gan",
        "price": 650000,
        "discountPrice": 550000,
        "description": "Củ sạc nhanh Anker Nano II 65W áp dụng công nghệ GaN II tiên tiến, giúp giảm kích thước củ sạc đến 58% so với sạc thông thường mà vẫn duy trì công suất sạc mạnh mẽ 65W. Phù hợp sạc cho MacBook, laptop chân sạc Type-C, iPhone và các dòng điện thoại Android phổ biến hiện nay.",
        "specs": {"Công suất tối đa": "65W", "Công nghệ": "GaN II", "Số cổng kết nối": "1x USB-C", "Trọng lượng": "112g"},
        "variants": [
            {"color": "Đen", "suffix": "BK", "price": 650000, "discountPrice": 550000, "stock": 100},
            {"color": "Trắng", "suffix": "WH", "price": 650000, "discountPrice": 550000, "stock": 80}
        ]
    },
    {
        "sku": "UGR-USBC100W",
        "name": "Cáp sạc Ugreen USB-C to USB-C 100W 2m",
        "brand": "Ugreen",
        "subcat": "cable-usbc",
        "price": 250000,
        "discountPrice": 180000,
        "description": "Cáp sạc nhanh Ugreen USB-C sang USB-C hỗ trợ công suất sạc tối đa lên tới 100W (20V/5A), hỗ trợ truyền tải dữ liệu tốc độ cao 480Mbps. Cáp bọc dù siêu bền chống đứt gãy, chiều dài 2 mét tiện lợi kết nối ở khoảng cách xa.",
        "specs": {"Chiều dài": "2m", "Công suất hỗ trợ": "Tối đa 100W (5A)", "Chất liệu vỏ": "Nylon bọc dù cao cấp", "Tốc độ truyền dữ liệu": "480Mbps"},
        "variants": [
            {"color": "Đen Space", "suffix": "SBK", "price": 250000, "discountPrice": 180000, "stock": 200},
            {"color": "Xám Space", "suffix": "SGR", "price": 250000, "discountPrice": 180000, "stock": 150}
        ]
    },
    {
        "sku": "BEL-USBCLTG",
        "name": "Cáp sạc nhanh Belkin BoostCharge USB-C to Lightning 1.2m",
        "brand": "Belkin",
        "subcat": "cable-lightning",
        "price": 390000,
        "discountPrice": 290000,
        "description": "Cáp sạc nhanh Belkin BoostCharge đạt chứng chỉ MFi của Apple, đảm bảo an toàn tuyệt đối và sạc nhanh tối ưu cho các thiết bị iPhone, iPad dùng cổng Lightning. Dây cáp được thử nghiệm uốn cong hơn 8,000 lần, mang lại độ bền cơ học ấn tượng.",
        "specs": {"Chiều dài": "1.2m", "Chứng chỉ": "MFi Apple", "Chất liệu đầu cáp": "Nhôm anode siêu bền", "Kiểu kết nối": "USB-C sang Lightning"},
        "variants": [
            {"color": "Đen", "suffix": "BK", "price": 390000, "discountPrice": 290000, "stock": 120},
            {"color": "Trắng", "suffix": "WH", "price": 390000, "discountPrice": 290000, "stock": 140}
        ]
    },
    {
        "sku": "MOPH-3IN1MAG",
        "name": "Đế sạc không dây 3-in-1 Mophie Magsafe",
        "brand": "Mophie",
        "subcat": "adapter-wireless",
        "price": 2490000,
        "discountPrice": 2190000,
        "description": "Đế sạc không dây cao cấp 3-trong-1 từ Mophie tích hợp công nghệ hít nam châm MagSafe chuẩn Apple, hỗ trợ sạc đồng thời 3 thiết bị: iPhone (15W), Apple Watch và tai nghe AirPods. Bề mặt hoàn thiện bằng chất liệu vải nỉ cao cấp mang lại vẻ sang trọng cho bàn làm việc.",
        "specs": {"Công suất MagSafe": "15W", "Cổng sạc Apple Watch": "Tích hợp sẵn", "Cổng sạc AirPods": "5W không dây", "Nguồn vào": "USB-C PD"},
        "variants": [
            {"color": "Đen Classic", "suffix": "BK", "price": 2490000, "discountPrice": 2190000, "stock": 50}
        ]
    },
    {
        "sku": "APL-TB4PRO",
        "name": "Cáp Thunderbolt 4 Pro Apple 1.8m",
        "brand": "Apple",
        "subcat": "cable-thunderbolt",
        "price": 3490000,
        "discountPrice": 3190000,
        "description": "Cáp Thunderbolt 4 Pro chính hãng Apple hỗ trợ truyền dữ liệu tốc độ cực cao lên tới 40Gbps, hỗ trợ xuất hình ảnh DisplayPort (HBR3) và sạc nhanh công suất lên tới 100W. Cáp bọc dù màu đen cao cấp, chống rối và hạn chế mài mòn tối đa.",
        "specs": {"Tốc độ băng thông": "Tối đa 40Gbps", "Chiều dài": "1.8m", "Xuất hình ảnh": "Hỗ trợ 4K/5K/6K/8K", "Công suất sạc": "100W"},
        "variants": [
            {"color": "Đen", "suffix": "BK", "price": 3490000, "discountPrice": 3190000, "stock": 30}
        ]
    },
    {
        "sku": "JBL-TOURPRO2",
        "name": "Tai nghe True Wireless JBL Tour Pro 2",
        "brand": "JBL",
        "subcat": "audio-tws",
        "price": 5990000,
        "discountPrice": 4990000,
        "description": "JBL Tour Pro 2 là dòng tai nghe True Wireless cao cấp sở hữu hộp sạc thông minh đầu tiên trên thế giới tích hợp màn hình cảm ứng LCD 1.45 inch. Tai nghe tích hợp công nghệ chống ồn chủ động thích ứng True Adaptive Noise Cancelling cùng âm thanh vòm JBL Spatial Sound sống động.",
        "specs": {"Thời lượng pin": "Lên tới 40 giờ (kèm hộp sạc)", "Chống ồn": "True Adaptive ANC", "Màn hình hộp sạc": "1.45 inch cảm ứng", "Kết nối": "Bluetooth 5.3"},
        "variants": [
            {"color": "Đen", "suffix": "BK", "price": 5990000, "discountPrice": 4990000, "stock": 60},
            {"color": "Vàng Champagne", "suffix": "GD", "price": 5990000, "discountPrice": 4990000, "stock": 45}
        ]
    },
    {
        "sku": "SONY-WH1000XM5",
        "name": "Tai nghe chụp tai chống ồn Sony WH-1000XM5",
        "brand": "Sony",
        "subcat": "audio-overear",
        "price": 8490000,
        "discountPrice": 6990000,
        "description": "Tai nghe chụp tai không dây chống ồn đỉnh cao Sony WH-1000XM5 trang bị bộ xử lý tích hợp V1 cùng bộ xử lý chống ồn HD QN1, mang lại khả năng chống ồn tốt nhất hiện nay. Hỗ trợ âm thanh độ phân giải cao Hi-Res Audio Wireless cùng thời lượng pin lên đến 30 giờ liên tục.",
        "specs": {"Driver": "30mm dynamic", "Trọng lượng": "250g", "Thời lượng pin": "30 giờ (bật ANC)", "Sạc nhanh": "Sạc 3 phút dùng 3 giờ"},
        "variants": [
            {"color": "Đen Classic", "suffix": "BK", "price": 8490000, "discountPrice": 6990000, "stock": 80},
            {"color": "Bạc Platinum", "suffix": "SL", "price": 8490000, "discountPrice": 6990000, "stock": 70},
            {"color": "Xanh Navy", "suffix": "BL", "price": 8490000, "discountPrice": 6990000, "stock": 50}
        ]
    },
    {
        "sku": "SONY-FLOATRUN",
        "name": "Tai nghe thể thao Sony Float Run WI-OE610",
        "brand": "Sony",
        "subcat": "audio-sport",
        "price": 2990000,
        "discountPrice": 2390000,
        "description": "Sony Float Run WI-OE610 sở hữu thiết kế tai nghe mở (off-ear) độc đáo dành riêng cho người chạy bộ và chơi thể thao. Thiết kế này giúp người dùng nghe nhạc thoải mái mà không bị bí tai, đồng thời dễ dàng nhận biết âm thanh từ môi trường xung quanh để đảm bảo an toàn.",
        "specs": {"Thiết kế": "Off-ear (Không nhét tai)", "Trọng lượng": "33g", "Thời lượng pin": "10 giờ liên tục", "Chống nước": "IPX4"},
        "variants": [
            {"color": "Đen", "suffix": "BK", "price": 2990000, "discountPrice": 2390000, "stock": 110}
        ]
    },
    {
        "sku": "RAZ-BSV2PRO",
        "name": "Tai nghe Gaming không dây Razer BlackShark V2 Pro",
        "brand": "Razer",
        "subcat": "audio-gaming",
        "price": 4990000,
        "discountPrice": 4290000,
        "description": "Tai nghe gaming không dây chuyên nghiệp Razer BlackShark V2 Pro trang bị công nghệ kết nối không dây Razer HyperSpeed Wireless siêu tốc, màng loa Razer TriForce Titanium 50mm cao cấp và micro siêu rộng Razer HyperClear Super Wideband cho chất lượng đàm thoại phòng thu.",
        "specs": {"Tần số đáp ứng": "12Hz - 28kHz", "Màng loa": "TriForce Titanium 50mm", "Microphone": "Super Wideband tháo rời", "Thời lượng pin": "Đến 70 giờ"},
        "variants": [
            {"color": "Đen", "suffix": "BK", "price": 4990000, "discountPrice": 4290000, "stock": 90},
            {"color": "Trắng", "suffix": "WH", "price": 4990000, "discountPrice": 4290000, "stock": 70}
        ]
    },
    {
        "sku": "BAS-GAN5100W",
        "name": "Củ sạc nhanh Baseus GaN5 Pro 100W",
        "brand": "Baseus",
        "subcat": "adapter-gan",
        "price": 950000,
        "discountPrice": 790000,
        "description": "Củ sạc Baseus GaN5 Pro sở hữu công suất sạc 100W siêu nhanh cùng thiết kế gọn nhẹ, trang bị 2 cổng USB-C và 1 cổng USB-A tiện dụng. Tích hợp công nghệ kiểm soát nhiệt độ thông minh BCT độc quyền của Baseus đảm bảo sạc an toàn, không quá nhiệt.",
        "specs": {"Số cổng": "3 cổng (2x Type-C, 1x USB-A)", "Công nghệ": "GaN5 Pro", "Công suất cổng C1/C2": "Tối đa 100W", "Trọng lượng": "140g"},
        "variants": [
            {"color": "Đen", "suffix": "BK", "price": 950000, "discountPrice": 790000, "stock": 150},
            {"color": "Trắng", "suffix": "WH", "price": 950000, "discountPrice": 790000, "stock": 100}
        ]
    },
    {
        "sku": "UGR-NEX140W",
        "name": "Củ sạc nhanh Ugreen Nexode 140W GaN 3 cổng",
        "brand": "Ugreen",
        "subcat": "adapter-multiport",
        "price": 1890000,
        "discountPrice": 1490000,
        "description": "Củ sạc Ugreen Nexode 140W GaN hỗ trợ chuẩn sạc Power Delivery 3.1 mới nhất, cho phép sạc đầy 50% pin MacBook Pro 16 inch chỉ trong vòng 30 phút. Thiết kế 3 cổng (2x USB-C, 1x USB-A) sạc đồng thời 3 thiết bị hiệu quả và an toàn.",
        "specs": {"Chuẩn sạc": "PD 3.1 / PPS / QC 4+", "Tổng công suất": "140W", "Phân phối dòng điện": "Tự động phân bổ thông minh", "Trọng lượng": "290g"},
        "variants": [
            {"color": "Xám Space", "suffix": "GR", "price": 1890000, "discountPrice": 1490000, "stock": 80}
        ]
    },
    {
        "sku": "ANK-PR20K",
        "name": "Sạc dự phòng Anker Prime 20,000mAh 200W",
        "brand": "Anker",
        "subcat": "adapter-gan",
        "price": 2990000,
        "discountPrice": 2490000,
        "description": "Sạc dự phòng Anker Prime 20,000mAh sở hữu dung lượng lưu trữ cực khủng cùng công suất sạc ra cực đại lên đến 200W tổng cộng, cho phép sạc nhanh MacBook Pro và iPad cùng một lúc. Màn hình màu kỹ thuật số thông minh hiển thị chi tiết công suất sạc và thời gian nạp đầy.",
        "specs": {"Dung lượng pin": "20,000mAh / 72Wh", "Công suất ra tối đa": "200W tổng", "Màn hình": "TFT LCD thông minh", "Số cổng sạc": "2x USB-C, 1x USB-A"},
        "variants": [
            {"color": "Đen Classic", "suffix": "BK", "price": 2990000, "discountPrice": 2490000, "stock": 70}
        ]
    },
    {
        "sku": "MAR-MOTIF2",
        "name": "Tai nghe True Wireless Marshall Motif II A.N.C.",
        "brand": "Marshall",
        "subcat": "audio-tws",
        "price": 4990000,
        "discountPrice": 4490000,
        "description": "Tai nghe True Wireless Marshall Motif II A.N.C mang đến chất âm Marshall đặc trưng mạnh mẽ trong một thiết kế bọc giả da cổ điển cực kỳ phong cách. Tích hợp công nghệ chống ồn chủ động ANC cải tiến cùng chế độ xuyên âm Transparency Mode mượt mà.",
        "specs": {"Driver": "6mm dynamic", "Kết nối": "Bluetooth 5.3 LE", "Thời lượng pin": "Lên tới 30 giờ (kèm ANC)", "Chuẩn chống nước": "IPX5 (tai nghe), IPX4 (hộp sạc)"},
        "variants": [
            {"color": "Đen", "suffix": "BK", "price": 4990000, "discountPrice": 4490000, "stock": 65}
        ]
    },
    {
        "sku": "RAZ-BWV4PRO",
        "name": "Bàn phím cơ không dây Razer BlackWidow V4 Pro",
        "brand": "Razer",
        "subcat": None,
        "price": 6490000,
        "discountPrice": 5690000,
        "description": "Razer BlackWidow V4 Pro là bàn phím cơ không dây đỉnh cao dành cho game thủ chuyên nghiệp. Sử dụng switch cơ học Razer Green/Yellow siêu nhạy, núm xoay đa chức năng Razer Dial, hệ thống phím macro chuyên dụng và đèn LED RGB Razer Chroma rực rỡ.",
        "specs": {"Switch cơ": "Razer Green (Clicky) / Yellow (Linear)", "Đèn LED": "Razer Chroma RGB", "Kết nối": "Không dây 2.4GHz / Bluetooth / Dây cáp", "Chất liệu keycap": "ABS Double-shot"},
        "variants": [
            {"color": "Đen", "suffix": "BK", "price": 6490000, "discountPrice": 5690000, "stock": 40}
        ]
    },
    {
        "sku": "RAZ-BASV3PRO",
        "name": "Chuột Gaming không dây Razer Basilisk V3 Pro",
        "brand": "Razer",
        "subcat": None,
        "price": 4290000,
        "discountPrice": 3790000,
        "description": "Chuột gaming không dây cao cấp Razer Basilisk V3 Pro sở hữu mắt đọc quang học Razer Focus Pro 30K siêu chính xác và Switch quang học chuột Razer Gen-3 độ bền 90 triệu click. Tích hợp con cuộn thông minh Razer HyperScroll Tilt Wheel độc đáo.",
        "specs": {"Cảm biến": "Focus Pro 30K Optical", "Độ phân giải tối đa": "30,000 DPI", "Số nút bấm": "11 nút lập trình được", "Kết nối": "HyperSpeed Wireless / Bluetooth / Type-C"},
        "variants": [
            {"color": "Đen Classic", "suffix": "BK", "price": 4290000, "discountPrice": 3790000, "stock": 80},
            {"color": "Trắng Mercury", "suffix": "WH", "price": 4290000, "discountPrice": 3790000, "stock": 60}
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

        # Lấy danh sách active services để gán luôn cho phụ kiện
        res_services = await conn.execute(
            text("SELECT id, code FROM attached_services WHERE is_active = TRUE AND code IN ('VIP-1D1-ACCESSORY-12M', 'S24-ACCESSORY-12M')")
        )
        services = res_services.fetchall()
        service_ids = [s.id for s in services]
        print(f"Loaded active accessory services: {[s.code for s in services]}")

        for p_data in PRODUCTS_TO_SEED:
            brand_id = BRANDS.get(p_data["brand"])
            subcat_id = SUBCATEGORIES.get(p_data["subcat"]) if p_data["subcat"] else None
            
            product_uuid = uuid4()
            slug = p_data["sku"].lower()
            
            # Gán attached services cho sales_config
            sales_config = {
                "attachedServices": [{"serviceId": str(s_id)} for s_id in service_ids]
            }

            # Build options JSON
            colors = [v["color"] for v in p_data["variants"]]
            options = []
            if len(colors) > 0 and colors[0] != "Đen": # chỉ tạo option nếu thực sự có biến thể phân biệt
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
                    "subcategory_id": subcat_id,
                    "brand_id": brand_id,
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

        print("\nSuccessfully seeded 15 technology accessories with variants and inventory.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
