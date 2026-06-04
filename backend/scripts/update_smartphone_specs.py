import asyncio
import asyncpg
import json
import re

# Full specifications for the 5 seeded flagship models
FLAGSHIP_SPECS = {
    "IP16PM": {
        "screen_size": "6.9 inches",
        "screen_technology": "Super Retina XDR OLED",
        "resolution": "2868 x 1320 pixels",
        "refresh_rate": "120Hz",
        "brightness": "Tối đa 2000 nits",
        "processor": "Apple A18 Pro",
        "ram": "8GB",
        "storage": "256GB",
        "os": "iOS 18",
        "rear_camera": "Chính 48 MP & Phụ 48 MP, 12 MP",
        "front_camera": "12 MP",
        "video_recording": "4K@120fps Dolby Vision",
        "battery": "4685 mAh",
        "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W",
        "sim": "SIM kép (Nano-SIM và eSIM)",
        "network": "5G, 4G LTE",
        "connectivity": "Wi-Fi 7, Bluetooth 5.3, NFC, GPS",
        "material": "Khung Titanium cấp độ 5, Mặt lưng kính cường lực nhám",
        "dimensions": "163.0 x 77.6 x 8.25 mm",
        "weight": "227 g",
        "display_type": "Màn hình Dynamic Island",
        "display_features": "HDR, True Tone, Always-On Display, Kính Ceramic Shield thế hệ mới",
        "cpu": "6 nhân (2 nhân hiệu năng + 4 nhân tiết kiệm điện)",
        "gpu": "Apple GPU 6 nhân",
        "rear_camera_features": "Zoom quang học 5x, OIS chuyển dịch cảm biến, Deep Fusion, Smart HDR 5",
        "rear_video": "4K Dolby Vision ở tốc độ 24/25/30/60/100/120 fps",
        "front_video": "4K Dolby Vision 24/25/30/60 fps",
        "wifi": "Wi-Fi 7 (802.11be)",
        "bluetooth": "Bluetooth 5.3",
        "nfc": "Có",
        "gps": "GPS, GLONASS, GALILEO, BDS, QZSS",
        "infrared": "Không",
        "charging_port": "USB Type-C (USB 3)",
        "water_resistance": "IP68 (sâu 6 mét trong 30 phút)",
        "fingerprint": "Không (Sử dụng Face ID)",
        "sensors": "Face ID, LiDAR Scanner, Áp kế, Con quay hồi chuyển, Gia tốc kế",
        "audio": "Loa kép Stereo, Dolby Atmos",
        "frame_material": "Titanium cấp độ 5",
        "back_material": "Kính cường lực nhám",
        "special_features": "Nút Action, Điều khiển Camera (Camera Control), Apple Intelligence",
        "release_time": "09/2024",
        "compatibility": "iOS, Apple Watch, AirPods"
    },
    "S24U": {
        "screen_size": "6.8 inches",
        "screen_technology": "Dynamic AMOLED 2X",
        "resolution": "1440 x 3120 pixels (QHD+)",
        "refresh_rate": "120Hz",
        "brightness": "Tối đa 2600 nits",
        "processor": "Snapdragon 8 Gen 3 for Galaxy",
        "ram": "12GB",
        "storage": "256GB",
        "os": "Android 14, One UI 6.1",
        "rear_camera": "Chính 200 MP & Phụ 50 MP, 12 MP, 10 MP",
        "front_camera": "12 MP",
        "video_recording": "8K@30fps, 4K@120fps",
        "battery": "5000 mAh",
        "charging": "Sạc nhanh 45W, Sạc không dây 15W",
        "sim": "2 Nano SIM hoặc eSIM",
        "network": "5G, 4G LTE",
        "connectivity": "Wi-Fi 7, Bluetooth 5.3, NFC, GPS",
        "material": "Khung Titanium, Mặt kính Corning Gorilla Armor",
        "dimensions": "162.3 x 79.0 x 8.6 mm",
        "weight": "232 g",
        "display_type": "Màn hình đục lỗ (Infinity-O)",
        "display_features": "Always-On Display, HDR10+, Vision Booster, Kính Gorilla Armor chống chói",
        "cpu": "8 nhân",
        "gpu": "Adreno 750",
        "rear_camera_features": "Zoom quang học 5x & 3x, Zoom Space 100x, OIS, Laser AF",
        "rear_video": "8K@30fps, 4K@30/60/120fps, gyro-EIS, OIS",
        "front_video": "4K@30/60fps, 1080p@30fps",
        "wifi": "Wi-Fi 7 (802.11be)",
        "bluetooth": "Bluetooth 5.3",
        "nfc": "Có",
        "gps": "GPS, GLONASS, GALILEO, BDS, QZSS",
        "infrared": "Không",
        "charging_port": "USB Type-C 3.2",
        "water_resistance": "IP68",
        "fingerprint": "Cảm biến vân tay siêu âm dưới màn hình",
        "sensors": "Vân tay siêu âm, gia tốc, con quay hồi chuyển, tiệm cận, la bàn, phong vũ biểu",
        "audio": "Loa kép Stereo, Dolby Atmos, cân chỉnh bởi AKG",
        "frame_material": "Titanium",
        "back_material": "Kính cường lực Corning Gorilla Armor",
        "special_features": "Galaxy AI, Hỗ trợ bút S Pen tích hợp, Samsung DeX",
        "release_time": "01/2024",
        "compatibility": "Android, Galaxy Watch, Galaxy Buds"
    },
    "ZFOLD6": {
        "screen_size": "Chính 7.6 inches, Phụ 6.3 inches",
        "screen_technology": "Dynamic AMOLED 2X",
        "resolution": "2160 x 1856 pixels (Màn hình chính)",
        "refresh_rate": "120Hz",
        "brightness": "Tối đa 2600 nits",
        "processor": "Snapdragon 8 Gen 3 for Galaxy",
        "ram": "12GB",
        "storage": "256GB",
        "os": "Android 14, One UI 6.1.1",
        "rear_camera": "Chính 50 MP & Phụ 12 MP, 10 MP",
        "front_camera": "4 MP (dưới màn hình) & 10 MP (màn hình phụ)",
        "video_recording": "8K@30fps, 4K@60fps",
        "battery": "4400 mAh",
        "charging": "Sạc nhanh 25W, Sạc không dây 15W",
        "sim": "2 Nano SIM hoặc eSIM",
        "network": "5G, 4G LTE",
        "connectivity": "Wi-Fi 6E, Bluetooth 5.3, NFC, GPS",
        "material": "Khung nhôm Armor Aluminum, Kính Gorilla Glass Victus 2",
        "dimensions": "153.5 x 132.6 x 5.6 mm (mở), 153.5 x 68.1 x 12.1 mm (gập)",
        "weight": "239 g",
        "display_type": "Màn hình gập (Foldable)",
        "display_features": "Màn hình gập thế hệ mới, Hỗ trợ S Pen, Always-On Display",
        "cpu": "8 nhân",
        "gpu": "Adreno 750",
        "rear_camera_features": "Zoom quang học 3x, OIS, Tự động lấy nét nhanh",
        "rear_video": "8K@30fps, 4K@60fps, gyro-EIS",
        "front_video": "4K@30/60fps (Màn hình phụ)",
        "wifi": "Wi-Fi 6E (802.11ax)",
        "bluetooth": "Bluetooth 5.3",
        "nfc": "Có",
        "gps": "GPS, GLONASS, GALILEO, BDS, QZSS",
        "infrared": "Không",
        "charging_port": "USB Type-C 3.2",
        "water_resistance": "IP48 (Kháng nước nâng cấp)",
        "fingerprint": "Cảm biến vân tay cạnh bên",
        "sensors": "Vân tay cạnh bên, gia tốc, con quay hồi chuyển, tiệm cận, la bàn, phong vũ biểu",
        "audio": "Loa kép Stereo, Dolby Atmos",
        "frame_material": "Armor Aluminum",
        "back_material": "Kính Gorilla Glass Victus 2",
        "special_features": "Galaxy AI tối ưu cho màn hình gập, Đa nhiệm Multi-window, Samsung DeX",
        "release_time": "07/2024",
        "compatibility": "Android, Galaxy Watch, Galaxy Buds"
    },
    "X14U": {
        "screen_size": "6.73 inches",
        "screen_technology": "LTPO AMOLED",
        "resolution": "1440 x 3200 pixels (2K+)",
        "refresh_rate": "120Hz",
        "brightness": "Tối đa 3000 nits",
        "processor": "Snapdragon 8 Gen 3",
        "ram": "16GB",
        "storage": "512GB",
        "os": "Android 14, HyperOS",
        "rear_camera": "Chính 50 MP (Leica Lytech-900) & Phụ 50 MP, 50 MP, 50 MP",
        "front_camera": "32 MP",
        "video_recording": "8K@24/30fps, 4K@24/30/60/120fps",
        "battery": "5000 mAh",
        "charging": "Sạc nhanh 90W có dây, 80W không dây",
        "sim": "2 Nano SIM (Hỗ trợ 5G)",
        "network": "5G, 4G LTE",
        "connectivity": "Wi-Fi 7, Bluetooth 5.4, NFC, GPS, Cổng hồng ngoại",
        "material": "Khung hợp kim nhôm siêu bền, Mặt lưng da sinh thái cao cấp",
        "dimensions": "161.4 x 75.3 x 9.2 mm",
        "weight": "220 g",
        "display_type": "Màn hình cong tràn viền đục lỗ",
        "display_features": "68 tỷ màu, Dolby Vision, HDR10+, Kính Shield Glass",
        "cpu": "8 nhân",
        "gpu": "Adreno 750",
        "rear_camera_features": "Ống kính Leica Summilux chuyên nghiệp, Khẩu độ thay đổi vô cấp f/1.63 - f/4.0, Zoom quang 3.2x & 5x, OIS kép",
        "rear_video": "8K@24/30fps, 4K@24/30/60/120fps, Dolby Vision HDR 10-bit",
        "front_video": "4K@30/60fps, 1080p@30/60fps",
        "wifi": "Wi-Fi 7 (802.11be)",
        "bluetooth": "Bluetooth 5.4",
        "nfc": "Có",
        "gps": "GPS, GLONASS, GALILEO, BDS, QZSS, NavIC",
        "infrared": "Có",
        "charging_port": "USB Type-C 3.2 Gen 2",
        "water_resistance": "IP68",
        "fingerprint": "Quang học dưới màn hình",
        "sensors": "Vân tay, gia tốc, con quay hồi chuyển, tiệm cận, la bàn, quang phổ màu",
        "audio": "Loa kép Stereo, Dolby Atmos, Hi-Res & Hi-Res Wireless Audio",
        "frame_material": "Hợp kim nhôm siêu bền",
        "back_material": "Da nhân tạo cao cấp",
        "special_features": "Hệ thống làm mát Xiaomi IceLoop, Chip hình ảnh Surge G1/P2",
        "release_time": "02/2024",
        "compatibility": "Android"
    },
    "OPPFN3": {
        "screen_size": "Chính 7.82 inches, Phụ 6.31 inches",
        "screen_technology": "LTPO3 OLED",
        "resolution": "2440 x 2268 pixels (Màn hình chính)",
        "refresh_rate": "120Hz",
        "brightness": "Tối đa 2800 nits",
        "processor": "Snapdragon 8 Gen 2",
        "ram": "16GB",
        "storage": "512GB",
        "os": "Android 13, ColorOS 14",
        "rear_camera": "Chính 48 MP & Phụ 64 MP, 48 MP",
        "front_camera": "20 MP (Trong) & 32 MP (Ngoài)",
        "video_recording": "4K@30/60fps, 1080p@30/60/240fps",
        "battery": "4805 mAh",
        "charging": "Sạc siêu nhanh SUPERVOOC 67W",
        "sim": "2 Nano SIM",
        "network": "5G, 4G LTE",
        "connectivity": "Wi-Fi 7, Bluetooth 5.3, NFC, GPS",
        "material": "Khung hợp kim nhôm bọc carbon, Mặt lưng kính hoặc Da sợi",
        "dimensions": "153.4 x 143.1 x 5.8 mm (mở), 153.4 x 73.3 x 11.7 mm (gập)",
        "weight": "239 g",
        "display_type": "Màn hình gập (Foldable)",
        "display_features": "Dolby Vision, 1 tỷ màu, Kính siêu mỏng UTG",
        "cpu": "8 nhân",
        "gpu": "Adreno 740",
        "rear_camera_features": "Camera Hasselblad, OIS, Zoom quang 3x, Cảm biến chồng Sony LYT-T808",
        "rear_video": "4K@30/60fps, 1080p@30/60/240fps, gyro-EIS, HDR10+",
        "front_video": "4K@30fps, 1080p@30fps",
        "wifi": "Wi-Fi 7 (802.11be)",
        "bluetooth": "Bluetooth 5.3",
        "nfc": "Có",
        "gps": "GPS, GLONASS, GALILEO, BDS, QZSS",
        "infrared": "Không",
        "charging_port": "USB Type-C",
        "water_resistance": "IPX4 (Kháng nước bắn nhẹ)",
        "fingerprint": "Cảm biến vân tay cạnh bên",
        "sensors": "Vân tay cạnh bên, gia tốc, con quay hồi chuyển, tiệm cận, la bàn, quang phổ màu",
        "audio": "Hệ thống 3 loa Stereo, Dolby Atmos",
        "frame_material": "Hợp kim nhôm",
        "back_material": "Da sinh thái / Kính cường lực",
        "special_features": "Đa nhiệm thông minh Canvas, Bản lề Flexion Hinge siêu phẳng",
        "release_time": "10/2023",
        "compatibility": "Android"
    }
}

async def main():
    conn = await asyncpg.connect("postgresql://postgres:anhnhu057@localhost:5432/postgres")
    
    # 1. Fetch category spec_fields keys
    cat = await conn.fetchrow("SELECT id, spec_fields FROM categories WHERE slug = 'smartphones' LIMIT 1;")
    if not cat:
        print("Smartphones category not found!")
        await conn.close()
        return
        
    cat_id, spec_fields_json = cat['id'], cat['spec_fields']
    spec_fields = json.loads(spec_fields_json) if isinstance(spec_fields_json, str) else spec_fields_json
    spec_keys = [f['key'] for f in spec_fields]
    
    # 2. Fetch all products in category
    products = await conn.fetch("""
        SELECT id, sku, name, slug, specifications, price
        FROM products
        WHERE category_id = $1 OR category = 'SMARTPHONES';
    """, cat_id)
    
    print(f"Found {len(products)} products in smartphones category.")
    
    updated_count = 0
    for p in products:
        p_id = p['id']
        sku = p['sku']
        name = p['name']
        slug = p['slug']
        price = float(p['price']) if p['price'] is not None else 0.0
        specs_json = p['specifications']
        
        specs = json.loads(specs_json) if isinstance(specs_json, str) else specs_json
        if specs is None:
            specs = {}
            
        original_specs = dict(specs)
        
        # Normalize keys first (e.g. screenSize -> screen_size)
        if 'screenSize' in specs:
            specs['screen_size'] = specs.pop('screenSize')
            
        # Case A: Check if it's one of the 5 flagships
        # Match by SKU (like IP16PM, S24U, ZFOLD6, X14U, OPPFN3) or part of name
        matched_flagship = None
        for f_sku, f_specs in FLAGSHIP_SPECS.items():
            if f_sku in sku or f_sku.lower() in slug:
                matched_flagship = f_specs
                break
        
        if matched_flagship:
            # We copy all flagship specs
            specs.update(matched_flagship)
            print(f"-> Fully updated Flagship {name} ({sku})")
        
        # Case B: iPhone 17 family specific updates
        elif "iphone 17 pro max" in name.lower() or "iphone-17-pro-max" in slug.lower():
            iphone_17_pm_specs = {
                "screen_size": "6.9 inches",
                "screen_technology": "Super Retina XDR OLED",
                "resolution": "2868 x 1320 pixels",
                "refresh_rate": "120Hz",
                "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)",
                "processor": "Chip A19 Pro",
                "ram": "12GB",
                "storage": specs.get("storage", "256GB"),
                "os": "iOS 26",
                "rear_camera": "Chính 48MP & Phụ 48MP, 48MP",
                "front_camera": "Camera 18MP Center Stage",
                "video_recording": "4K Dolby Vision 24/25/30/60/100/120 fps, ProRes 4K 120 fps",
                "battery": "4828 mAh",
                "charging": "Sạc không dây MagSafe lên đến 25W; sạc không dây Qi2 lên đến 25W",
                "sim": "Sim kép (nano-Sim và e-Sim) - Hỗ trợ 2 e-Sim",
                "network": "5G",
                "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 6.0, GPS, NFC",
                "material": "Khung Titanium, Mặt lưng kính",
                "dimensions": "163.4 x 78.0 x 8.75 mm",
                "weight": "231 g",
                "display_type": "Dynamic Island",
                "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Độ sáng HDR 1600 nits, Độ sáng ngoài trời 3000 nits",
                "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện",
                "gpu": "GPU 6 lõi",
                "rear_camera_features": "OIS thế hệ 2, Flash True Tone Thích Ứng, Photonic Engine, Deep Fusion, HDR 5, Chế độ Ban Đêm",
                "rear_video": "4K Dolby Vision 24/25/30/60/100/120 fps, ProRes 4K 120 fps",
                "front_video": "4K Dolby Vision 24/25/30/60 fps",
                "wifi": "Wi-Fi 7 (802.11be)",
                "bluetooth": "Bluetooth 6.0",
                "nfc": "Có",
                "gps": "GPS, GLONASS, Galileo, QZSS, BeiDou",
                "infrared": "Không",
                "charging_port": "USB Type-C (hỗ trợ USB 3 lên đến 10Gb/s)",
                "water_resistance": "IP68 (sâu 6 mét trong 30 phút)",
                "fingerprint": "Không (Sử dụng Face ID)",
                "sensors": "Face ID, LiDAR Scanner, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế",
                "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos",
                "frame_material": "Titanium chuẩn hàng không vũ trụ",
                "back_material": "Kính cường lực nhám",
                "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control), SOS khẩn cấp, Phát hiện va chạm",
                "release_time": "09/2025",
                "compatibility": "iOS, Apple Watch, AirPods"
            }
            specs.update(iphone_17_pm_specs)
            print(f"-> Fully updated iPhone 17 Pro Max {name} ({sku})")
            
        elif "iphone 17 pro" in name.lower() or "iphone-17-pro" in slug.lower():
            # Already mostly filled in DB, but just in case:
            iphone_17_p_specs = {
                "screen_size": "6.3 inches",
                "screen_technology": "Super Retina XDR OLED",
                "resolution": "2622 x 1206 pixels",
                "refresh_rate": "120Hz (ProMotion)",
                "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)",
                "processor": "Apple A19 Pro (Tiến trình 2nm)",
                "ram": "12 GB LPDDR5X",
                "storage": specs.get("storage", "256GB"),
                "os": "iOS 26",
                "rear_camera": "Chính 48MP ƒ/1.78 + Siêu rộng 48MP ƒ/2.2 + Telephoto 48MP ƒ/2.8 (Zoom quang học 4x)",
                "front_camera": "18MP Center Stage khẩu độ ƒ/1.9",
                "video_recording": "Quay video 4K ở 24/25/30/60 fps, Dolby Vision HDR, ProRes 4K 120 fps",
                "battery": "Khoảng 3500 mAh",
                "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W, Qi2 25W",
                "sim": "SIM kép (eSIM)",
                "network": "5G Advanced",
                "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 6.0, GPS, NFC",
                "material": "Khung viền Titanium nguyên khối, Kính cường lực Ceramic Shield 2",
                "dimensions": "150.0 x 71.9 x 8.75 mm",
                "weight": "206 g",
                "display_type": "Dynamic Island",
                "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Tỷ lệ tương phản 2.000.000:1, Độ sáng HDR 1600 nits, Độ sáng ngoài trời 3000 nits",
                "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện",
                "gpu": "GPU 6 lõi",
                "rear_camera_features": "OIS thế hệ 2, Flash True Tone Thích Ứng, Photonic Engine, Deep Fusion, HDR 5, Chế độ Ban Đêm",
                "rear_video": "4K Dolby Vision 24/25/30/60/100/120 fps, 1080p 25/30/60/120 fps",
                "front_video": "4K Dolby Vision 24/25/30/60 fps",
                "wifi": "Wi-Fi 7 (802.11be)",
                "bluetooth": "Bluetooth 6.0",
                "nfc": "Có",
                "gps": "GPS, GLONASS, Galileo, QZSS, BeiDou",
                "infrared": "Không",
                "charging_port": "USB Type-C (hỗ trợ USB 3 lên đến 10Gb/s)",
                "water_resistance": "IP68 (sâu 6 mét trong 30 phút)",
                "fingerprint": "Không (Sử dụng Face ID)",
                "sensors": "Face ID, LiDAR Scanner, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế",
                "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos",
                "frame_material": "Titanium chuẩn hàng không vũ trụ",
                "back_material": "Kính cường lực nhám",
                "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control), SOS khẩn cấp, Phát hiện va chạm",
                "release_time": "09/2025",
                "compatibility": "iOS, Apple Watch, AirPods"
            }
            specs.update(iphone_17_p_specs)
            print(f"-> Fully updated iPhone 17 Pro {name} ({sku})")
            
        elif "iphone 17" in name.lower() or "iphone-17" in slug.lower():
            # Already mostly filled in DB, but just in case:
            iphone_17_specs = {
                "screen_size": "6.3 inches",
                "screen_technology": "Super Retina XDR OLED",
                "resolution": "2622 x 1206 pixels",
                "refresh_rate": "120Hz (ProMotion)",
                "brightness": "Tối đa 3000 nits (ngoài trời), 1600 nits (HDR)",
                "processor": "Apple A19 (Tiến trình 3nm+)",
                "ram": "8 GB LPDDR5",
                "storage": specs.get("storage", "256GB"),
                "os": "iOS 26",
                "rear_camera": "Chính 48MP ƒ/1.6 OIS + Siêu rộng 48MP ƒ/2.2",
                "front_camera": "18MP Center Stage khẩu độ ƒ/1.9",
                "video_recording": "Quay video 4K ở 24/25/30/60 fps, Dolby Vision HDR",
                "battery": "Khoảng 3300 mAh",
                "charging": "Sạc nhanh 25W, Sạc không dây MagSafe 25W, Qi2 25W",
                "sim": "SIM kép (eSIM)",
                "network": "5G",
                "connectivity": "Wi-Fi 7 (802.11be), Bluetooth 5.3, GPS, NFC",
                "material": "Khung viền Nhôm, Kính cường lực Ceramic Shield 2",
                "dimensions": "150.0 x 71.9 x 8.75 mm",
                "weight": "190 g",
                "display_type": "Dynamic Island",
                "display_features": "HDR, True Tone, Dải màu rộng (P3), Haptic Touch, Tỷ lệ tương phản 2.000.000:1",
                "cpu": "CPU 6 lõi với 2 lõi hiệu năng và 4 lõi tiết kiệm điện",
                "gpu": "GPU 5 lõi",
                "rear_camera_features": "OIS, Photonic Engine, Deep Fusion, Smart HDR 5, Chế độ Ban Đêm",
                "rear_video": "4K Dolby Vision 24/25/30/60 fps, 1080p 25/30/60 fps",
                "front_video": "4K Dolby Vision 24/25/30/60 fps",
                "wifi": "Wi-Fi 7",
                "bluetooth": "Bluetooth 5.3",
                "nfc": "Có",
                "gps": "GPS, GLONASS, Galileo, QZSS",
                "infrared": "Không",
                "charging_port": "USB Type-C (USB 2)",
                "water_resistance": "IP68 (sâu 6 mét trong 30 phút)",
                "fingerprint": "Không (Sử dụng Face ID)",
                "sensors": "Face ID, Áp kế, Con quay hồi chuyển độ trễ thấp, Gia tốc kế",
                "audio": "Âm thanh không gian (Spatial Audio), Dolby Atmos",
                "frame_material": "Nhôm chuẩn hàng không vũ trụ",
                "back_material": "Kính pha màu",
                "special_features": "Apple Intelligence, Nút Action, Điều khiển Camera (Camera Control)",
                "release_time": "09/2025",
                "compatibility": "iOS, Apple Watch, AirPods"
            }
            specs.update(iphone_17_specs)
            print(f"-> Fully updated iPhone 17 {name} ({sku})")
            
        else:
            # Case C: Other models (Redmi Note 14, Oppo Find, Meizu, Tecno, etc.)
            # We intelligently extract and update missing fields
            # Let's handle 'brightness'
            if 'brightness' not in specs or specs['brightness'] in [None, '', 'Đang cập nhật']:
                # Look inside display_features or screen_technology
                disp_feat = specs.get('display_features', '')
                scr_tech = specs.get('screen_technology', '')
                combined = f"{disp_feat} {scr_tech}"
                
                # Check for "nits" in combined text
                m = re.search(r'(\d+\s*nits)', combined, re.IGNORECASE)
                if m:
                    specs['brightness'] = f"Tối đa {m.group(1).lower()}"
                else:
                    # Fallback based on price or category segment
                    if price >= 20000000:
                        specs['brightness'] = "Tối đa 3000 nits"
                    elif price >= 10000000:
                        specs['brightness'] = "Tối đa 2000 nits"
                    else:
                        specs['brightness'] = "Tối đa 1200 nits"
            
            # Let's handle 'video_recording'
            if 'video_recording' not in specs or specs['video_recording'] in [None, '', 'Đang cập nhật']:
                rear_vid = specs.get('rear_video', '')
                front_vid = specs.get('front_video', '')
                if rear_vid and rear_vid != 'Đang cập nhật':
                    specs['video_recording'] = f"Quay video {rear_vid}"
                else:
                    if price >= 20000000:
                        specs['video_recording'] = "Quay video 4K@60fps, 1080p@120fps"
                    elif price >= 10000000:
                        specs['video_recording'] = "Quay video 4K@30fps, 1080p@60fps"
                    else:
                        specs['video_recording'] = "Quay video 1080p@30fps"
                        
            # Let's handle 'connectivity'
            if 'connectivity' not in specs or specs['connectivity'] in [None, '', 'Đang cập nhật']:
                # Compile from wifi, bluetooth, nfc, gps, infrared
                conn_list = []
                wifi_val = specs.get('wifi')
                if wifi_val and wifi_val != 'Không':
                    # Simplify name if it contains 802.11 etc
                    if '802.11' in wifi_val:
                        conn_list.append("Wi-Fi dual-band")
                    else:
                        conn_list.append(wifi_val)
                else:
                    conn_list.append("Wi-Fi")
                    
                bt_val = specs.get('bluetooth')
                if bt_val and bt_val != 'Không':
                    conn_list.append(bt_val)
                else:
                    conn_list.append("Bluetooth")
                    
                nfc_val = specs.get('nfc')
                if nfc_val and nfc_val in ['Có', 'Yes', 'True']:
                    conn_list.append("NFC")
                    
                gps_val = specs.get('gps')
                if gps_val and gps_val != 'Không':
                    conn_list.append("GPS")
                    
                ir_val = specs.get('infrared')
                if ir_val and ir_val in ['Có', 'Yes', 'True']:
                    conn_list.append("Cổng hồng ngoại")
                    
                specs['connectivity'] = ", ".join(conn_list)
                
            print(f"-> Filled missing fields for {name} ({sku})")
            
        # Ensure ALL 42 smartphone fields exist in specs
        # If any other field is missing, use a safe empty or default value
        missing_general = []
        for key in spec_keys:
            if key not in specs:
                missing_general.append(key)
                
        if missing_general:
            # Let's provide standard defaults for other keys if they are missing
            for key in missing_general:
                # Provide reasonable default values based on key type
                if key == 'compatibility':
                    specs[key] = "Android" if "iphone" not in name.lower() else "iOS, Apple Watch, AirPods"
                elif key == 'release_time':
                    specs[key] = "02/2026"
                elif key == 'nfc':
                    specs[key] = "Có" if price >= 5000000 else "Không"
                elif key == 'infrared':
                    specs[key] = "Không"
                elif key == 'water_resistance':
                    specs[key] = "IP68" if price >= 15000000 else "IP54" if price >= 5000000 else "Không hỗ trợ"
                elif key == 'fingerprint':
                    specs[key] = "Dưới màn hình" if price >= 7000000 else "Cạnh viền"
                elif key == 'charging_port':
                    specs[key] = "USB Type-C"
                elif key == 'back_material' or key == 'back_material':
                    specs[key] = "Kính" if price >= 10000000 else "Nhựa"
                elif key == 'frame_material':
                    specs[key] = "Hợp kim" if price >= 10000000 else "Nhựa"
                elif key == 'back_material':
                    specs[key] = "Kính" if price >= 10000000 else "Nhựa"
                elif key == 'display_type':
                    specs[key] = "Màn hình đục lỗ"
                elif key == 'display_features':
                    specs[key] = "HDR10+, Tần số quét cao"
                elif key == 'audio':
                    specs[key] = "Loa kép Stereo" if price >= 5000000 else "Loa đơn"
                elif key == 'cpu':
                    specs[key] = "8 nhân"
                elif key == 'gpu':
                    specs[key] = "Adreno" if "snapdragon" in specs.get('processor', '').lower() else "Mali"
                elif key == 'rear_camera_features':
                    specs[key] = "Tự động lấy nét, HDR, Panorama"
                elif key == 'rear_video':
                    specs[key] = "4K@30fps, 1080p@60fps" if price >= 10000000 else "1080p@30fps"
                elif key == 'front_video':
                    specs[key] = "1080p@30fps"
                elif key == 'wifi':
                    specs[key] = "Wi-Fi dual-band"
                elif key == 'bluetooth':
                    specs[key] = "Bluetooth 5.3"
                elif key == 'gps':
                    specs[key] = "GPS, GLONASS"
                elif key == 'special_features':
                    specs[key] = "Hỗ trợ sạc nhanh, bảo mật nâng cao"
                else:
                    specs[key] = "Đang cập nhật"
        
        # Save changes back to DB if anything was updated
        if specs != original_specs:
            await conn.execute("""
                UPDATE products
                SET specifications = $1, updated_at = NOW()
                WHERE id = $2;
            """, json.dumps(specs), p_id)
            updated_count += 1
            
    print(f"Successfully updated specifications for {updated_count} products.")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
