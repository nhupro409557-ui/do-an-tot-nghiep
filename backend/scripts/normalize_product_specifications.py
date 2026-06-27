import asyncio
import json
import re

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"

PRODUCT_SPEC_OVERRIDES = {
    "RAZ-BWV4PRO": {
        "power": "Pin sạc tích hợp / USB-C",
        "ports": "USB-C, USB passthrough",
        "battery": "Không dây, thời lượng tùy chế độ đèn",
        "material": "Keycap ABS Double-shot",
        "color": "Đen",
        "dimensions": "Bàn phím full-size",
        "weight": "Đang cập nhật",
        "charging_standard": "USB-C",
    },
    "RAZ-BASV3PRO": {
        "power": "Pin sạc tích hợp / USB-C",
        "ports": "USB-C",
        "battery": "Tối đa khoảng 90 giờ tùy chế độ kết nối",
        "material": "Vỏ nhựa cao cấp",
        "color": "Đen / Trắng tùy phiên bản",
        "dimensions": "Chuột công thái học",
        "weight": "Khoảng 112g",
        "charging_standard": "USB-C",
    },
    "APL-MAGSAFE3": {
        "power": "Hỗ trợ sạc MacBook qua USB-C Power Adapter",
        "ports": "USB-C sang MagSafe 3",
        "charging_standard": "USB-C Power Delivery",
        "material": "Cáp bện",
        "color": "Trắng / Midnight tùy phiên bản",
        "dimensions": "Dài 2m",
        "battery": "Không áp dụng",
    },
    "BEL-USBCLTG": {
        "power": "Hỗ trợ sạc nhanh iPhone",
        "ports": "USB-C sang Lightning",
        "charging_standard": "USB Power Delivery, MFi",
        "color": "Trắng",
        "dimensions": "Dài 1.2m",
        "battery": "Không áp dụng",
    },
    "APL-TB4PRO": {
        "ports": "Thunderbolt 4 USB-C",
        "charging_standard": "USB Power Delivery tối đa 100W",
        "material": "Cáp bện Apple",
        "color": "Đen",
        "dimensions": "Dài 1.8m",
        "battery": "Không áp dụng",
    },
    "BAS-GAN5100W": {
        "power": "Tối đa 100W",
        "connectivity": "USB-C / USB-A",
        "material": "Nhựa chống cháy",
        "color": "Đen / Trắng tùy phiên bản",
        "dimensions": "Thiết kế nhỏ gọn",
        "battery": "Không áp dụng",
    },
    "BAS-GAN6-45W": {
        "connectivity": "USB-C",
        "material": "Nhựa chống cháy",
        "color": "Trắng",
        "dimensions": "Thiết kế nhỏ gọn",
        "weight": "Đang cập nhật",
        "battery": "Không áp dụng",
    },
    "UGR-NEX140W": {
        "ports": "2x USB-C, 1x USB-A",
        "connectivity": "USB-C / USB-A",
        "material": "Nhựa chống cháy",
        "color": "Xám",
        "dimensions": "Thiết kế để bàn/du lịch",
        "battery": "Không áp dụng",
    },
    "MOPH-3IN1MAG": {
        "power": "MagSafe 15W, Apple Watch, AirPods 5W",
        "ports": "USB-C nguồn vào",
        "connectivity": "MagSafe / Qi / Apple Watch magnetic charger",
        "charging_standard": "MagSafe, Qi",
        "material": "Đế gập du lịch",
        "color": "Đen",
        "dimensions": "Thiết kế gập mang theo",
        "battery": "Không áp dụng",
    },
    "UGR-HUB6IN1": {
        "power": "Hỗ trợ cấp nguồn qua USB-C tùy thiết bị",
        "connectivity": "USB-C sang HDMI/USB/SD/TF",
        "color": "Xám bạc",
        "dimensions": "Hub USB-C nhỏ gọn",
        "weight": "Đang cập nhật",
        "battery": "Không áp dụng",
    },
    "JBL-TOURPRO2": {
        "power": "Sạc qua USB-C / sạc không dây Qi",
        "ports": "USB-C trên hộp sạc",
        "charging_standard": "USB-C, Qi",
        "material": "Tai nghe true wireless",
        "color": "Đen / Champagne tùy phiên bản",
        "driver": "Driver dynamic 10mm",
        "microphone": "6 micro đàm thoại/chống ồn",
        "dimensions": "Tai nghe kèm hộp sạc thông minh",
        "weight": "Đang cập nhật",
    },
}


def as_dict(value) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def clean(value):
    if value in (None, "", [], {}):
        return None
    return str(value).strip()


def pick(specs: dict, *keys: str):
    for key in keys:
        value = clean(specs.get(key))
        if value:
            return value
    return None


def set_if_empty(specs: dict, key: str, value) -> None:
    value = clean(value)
    if value and not clean(specs.get(key)):
        specs[key] = value


def first_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(0) if match else None


def infer_screen(specs: dict) -> None:
    source = " ".join(
        filter(
            None,
            [
                pick(specs, "Màn hình", "Màn hình trong", "Kích thước màn", "Kích thước màn hình"),
                pick(specs, "screen_size"),
            ],
        )
    )
    if not source:
        return
    set_if_empty(specs, "screen_size", first_match(source, r"\d+(?:[.,]\d+)?\s*inch"))
    for tech in ["Dynamic AMOLED 2X", "Super AMOLED", "AMOLED", "OLED", "Liquid Retina", "IPS", "TFT LCD"]:
        if tech.lower() in source.lower():
            set_if_empty(specs, "screen_technology", tech)
            break
    refresh = first_match(source, r"\d+\s*Hz")
    if refresh:
        set_if_empty(specs, "refresh_rate", refresh)
    for resolution in ["QHD+", "WQHD+", "1.5K", "2K", "4K", "Full HD", "FHD", "HD+"]:
        if resolution.lower() in source.lower():
            set_if_empty(specs, "resolution", resolution)
            break


def infer_memory_from_name(specs: dict, name: str) -> None:
    ram = first_match(name, r"\d+\s*GB(?=/)")
    storage_match = re.search(r"/\s*(\d+\s*(?:GB|TB))", name, re.IGNORECASE)
    if ram:
        set_if_empty(specs, "ram", ram.replace(" ", ""))
    if storage_match:
        set_if_empty(specs, "storage", storage_match.group(1).replace(" ", ""))
    storage = first_match(name, r"\d+\s*(?:GB|TB)")
    if storage and not clean(specs.get("storage")):
        set_if_empty(specs, "storage", storage.replace(" ", ""))


def normalize_common_labels(specs: dict, name: str) -> None:
    mappings = {
        "processor": ["Chip xử lý", "Bộ xử lý", "CPU"],
        "storage": ["Bộ nhớ", "Bộ nhớ trong", "Dung lượng", "Ổ cứng"],
        "ram": ["RAM"],
        "battery": ["Dung lượng pin", "Thời lượng pin", "Pin"],
        "charging": ["Sạc nhanh", "Công nghệ sạc", "Sạc"],
        "connectivity": ["Kết nối", "Chuẩn kết nối", "Kết nối không dây"],
        "water_resistance": ["Chống nước", "Chuẩn chống nước", "Kháng nước"],
        "weight": ["Trọng lượng"],
        "dimensions": ["Kích thước"],
        "material": ["Chất liệu", "Chất liệu vỏ", "Chất liệu khung"],
        "ports": ["Cổng kết nối", "Số cổng", "Số cổng kết nối", "Cổng ra"],
        "power": ["Công suất tối đa", "Tổng công suất", "Công suất hỗ trợ", "Công suất sạc", "Công suất ra", "Công suất ra tối đa"],
        "capacity": ["Dung lượng", "Dung lượng pin"],
        "cable_length": ["Chiều dài"],
        "charging_standard": ["Chuẩn sạc", "Hỗ trợ chuẩn sạc"],
        "driver": ["Driver", "Màng loa"],
        "microphone": ["Microphone", "Micro"],
        "noise_cancellation": ["Chống ồn"],
    }
    for target, labels in mappings.items():
        set_if_empty(specs, target, pick(specs, *labels))
    infer_screen(specs)
    infer_memory_from_name(specs, name)


def normalize_phone(specs: dict, name: str, brand: str | None) -> None:
    normalize_common_labels(specs, name)
    set_if_empty(specs, "processor", pick(specs, "Chip xử lý", "Bộ xử lý"))
    set_if_empty(specs, "rear_camera", pick(specs, "Camera chính", "Camera sau", "Camera trước/sau"))
    set_if_empty(specs, "front_camera", pick(specs, "Camera trước", "Camera trước/sau"))
    set_if_empty(specs, "charging", pick(specs, "Sạc nhanh"))
    set_if_empty(specs, "battery", pick(specs, "Dung lượng pin"))
    set_if_empty(specs, "os", "Android" if (brand or "").lower() != "apple" else "iOS")
    set_if_empty(specs, "sim", "2 SIM hoặc eSIM tùy phiên bản")
    set_if_empty(specs, "network", "5G")
    set_if_empty(specs, "charging_port", "USB Type-C")
    set_if_empty(specs, "wifi", "Wi-Fi dual-band")
    set_if_empty(specs, "bluetooth", "Bluetooth 5.x")
    set_if_empty(specs, "gps", "GPS, GLONASS, Galileo")
    set_if_empty(specs, "audio", "Loa ngoài")
    set_if_empty(specs, "sensors", "Gia tốc, con quay, tiệm cận, ánh sáng")
    if "gập" in name.lower() or "flip" in name.lower():
        set_if_empty(specs, "special_features", pick(specs, "Bản lề") or "Thiết kế gập")
    set_if_empty(specs, "video_recording", "Quay video 4K hoặc Full HD tùy chế độ")


def normalize_tablet(specs: dict, name: str, brand: str | None) -> None:
    normalize_common_labels(specs, name)
    set_if_empty(specs, "screen_size", pick(specs, "Màn hình"))
    set_if_empty(specs, "processor", pick(specs, "Chip xử lý", "Bộ xử lý"))
    set_if_empty(specs, "storage", pick(specs, "Bộ nhớ trong", "Bộ nhớ"))
    set_if_empty(specs, "battery", pick(specs, "Dung lượng pin"))
    set_if_empty(specs, "charging", pick(specs, "Sạc nhanh"))
    set_if_empty(specs, "os", "iPadOS" if (brand or "").lower() == "apple" else "Android")
    set_if_empty(specs, "rear_camera", "12MP" if (brand or "").lower() == "apple" else "Đang cập nhật")
    set_if_empty(specs, "front_camera", "12MP" if (brand or "").lower() == "apple" else "Đang cập nhật")
    set_if_empty(specs, "connectivity", pick(specs, "Kết nối") or "Wi-Fi")
    set_if_empty(specs, "wifi", pick(specs, "Kết nối") or "Wi-Fi")
    set_if_empty(specs, "bluetooth", "Bluetooth 5.x")
    set_if_empty(specs, "audio", "Loa stereo")
    set_if_empty(specs, "charging_port", "USB Type-C")
    if "ipad pro m4" in name.lower():
        specs.update(
            {
                "screen_size": "11 inch",
                "screen_technology": "Ultra Retina XDR OLED",
                "resolution": "2420 x 1668 pixels",
                "refresh_rate": "ProMotion 120Hz",
                "processor": "Apple M4",
                "ram": specs.get("ram") or "8GB hoặc 16GB tùy dung lượng",
                "storage": specs.get("storage") or "256GB / 512GB / 1TB / 2TB",
                "os": "iPadOS",
                "rear_camera": "12MP Wide + LiDAR Scanner",
                "front_camera": "12MP Ultra Wide ngang",
                "charging": "USB-C Thunderbolt / USB 4",
                "connectivity": "Wi-Fi 6E, Bluetooth 5.3",
                "compatibility": "Apple Pencil Pro, Magic Keyboard",
            }
        )


def normalize_wearable(specs: dict, name: str, brand: str | None) -> None:
    normalize_common_labels(specs, name)
    set_if_empty(specs, "screen_size", pick(specs, "Màn hình", "Kích thước màn", "Kích thước mặt"))
    set_if_empty(specs, "processor", pick(specs, "Chip xử lý"))
    set_if_empty(specs, "storage", pick(specs, "Bộ nhớ"))
    set_if_empty(specs, "battery", pick(specs, "Thời lượng pin"))
    set_if_empty(specs, "sports_modes", pick(specs, "Số chế độ thể thao") or "Theo dõi luyện tập đa môn")
    set_if_empty(specs, "gps", pick(specs, "Hệ thống định vị") or "GPS")
    set_if_empty(specs, "connectivity", pick(specs, "Hỗ trợ cuộc gọi") or "Bluetooth")
    set_if_empty(specs, "compatibility", "iOS" if (brand or "").lower() == "apple" else "Android / iOS")
    set_if_empty(specs, "sensors", "Nhịp tim, SpO2, giấc ngủ, vận động")
    set_if_empty(specs, "water_resistance", "5ATM")
    set_if_empty(specs, "screen_technology", "AMOLED" if "amoled" in json.dumps(specs, ensure_ascii=False).lower() else "Đang cập nhật")
    set_if_empty(specs, "case_size", pick(specs, "Kích thước mặt"))
    set_if_empty(specs, "material", pick(specs, "Chất liệu vỏ", "Viền", "Chất liệu khung"))


def normalize_camera(specs: dict, name: str) -> None:
    normalize_common_labels(specs, name)
    set_if_empty(specs, "sensor", pick(specs, "Cảm biến", "Kích thước cảm biến"))
    set_if_empty(specs, "resolution", pick(specs, "Độ phân giải", "Độ phân giải video"))
    set_if_empty(specs, "video_recording", pick(specs, "Quay video", "Độ phân giải video", "Quay phim"))
    set_if_empty(specs, "stabilization", pick(specs, "Chống rung"))
    set_if_empty(specs, "field_of_view", pick(specs, "Góc nhìn", "Góc nhìn ống kính", "Góc xoay ngang"))
    set_if_empty(specs, "storage", pick(specs, "Hỗ trợ thẻ nhớ") or "Thẻ nhớ microSD tùy model")
    set_if_empty(specs, "connectivity", pick(specs, "Kết nối", "Kết nối không dây") or "Wi-Fi")
    set_if_empty(specs, "water_resistance", pick(specs, "Chống nước", "Chuẩn chống nước", "Kháng nước"))
    set_if_empty(specs, "microphone", pick(specs, "Đàm thoại") or "Tích hợp")
    set_if_empty(specs, "lens", pick(specs, "Ống kính") or "Đang cập nhật")
    set_if_empty(specs, "battery", pick(specs, "Dung lượng pin") or ("Pin rời" if "gopro" in name.lower() or "dji" in name.lower() else "Nguồn DC"))


def normalize_camera_photo(specs: dict) -> None:
    normalize_common_labels(specs, "")
    set_if_empty(specs, "sensor", pick(specs, "Cảm biến"))
    set_if_empty(specs, "resolution", pick(specs, "Cảm biến"))
    set_if_empty(specs, "iso", pick(specs, "Dải ISO"))
    set_if_empty(specs, "autofocus", pick(specs, "Hệ thống lấy nét", "Khả năng lấy nét"))
    set_if_empty(specs, "video_recording", pick(specs, "Quay video", "Quay phim"))
    set_if_empty(specs, "connectivity", pick(specs, "Kết nối không dây"))
    set_if_empty(specs, "lens", "Kèm lens kit" if "Lens" in json.dumps(specs, ensure_ascii=False) else "Body")
    set_if_empty(specs, "storage", "Thẻ SD")
    set_if_empty(specs, "battery", "Pin máy ảnh rời")


def normalize_laptop(specs: dict, name: str, brand: str | None) -> None:
    normalize_common_labels(specs, name)
    set_if_empty(specs, "processor", pick(specs, "CPU"))
    set_if_empty(specs, "graphics", pick(specs, "Card đồ họa"))
    set_if_empty(specs, "os", "Windows 11" if (brand or "").lower() != "apple" else "macOS")
    set_if_empty(specs, "wireless", "Wi-Fi 6/6E, Bluetooth")
    set_if_empty(specs, "webcam", "HD/FHD webcam")
    set_if_empty(specs, "audio", "Loa tích hợp")
    set_if_empty(specs, "keyboard", "Bàn phím có đèn nền")
    set_if_empty(specs, "ports", "USB-C, USB-A, HDMI hoặc Thunderbolt tùy phiên bản")
    if "gaming" in name.lower() or "rog" in name.lower() or "nitro" in name.lower():
        set_if_empty(specs, "refresh_rate", "144Hz hoặc cao hơn")
        set_if_empty(specs, "screen_technology", "IPS/OLED tùy phiên bản")


def normalize_accessory(specs: dict, name: str, subcategory: str | None) -> None:
    normalize_common_labels(specs, name)
    sub = (subcategory or "").lower()
    if "cáp" in sub or "cáp" in name.lower():
        set_if_empty(specs, "accessory_type", "Cáp sạc / truyền dữ liệu")
        set_if_empty(specs, "connectivity", pick(specs, "Kiểu kết nối", "Kết nối") or "USB-C")
        set_if_empty(specs, "cable_length", pick(specs, "Chiều dài"))
    elif "tai nghe" in sub or "tai nghe" in name.lower():
        set_if_empty(specs, "accessory_type", "Tai nghe")
        set_if_empty(specs, "connectivity", pick(specs, "Kết nối") or "Bluetooth")
        set_if_empty(specs, "battery", pick(specs, "Thời lượng pin"))
    elif "sạc" in sub or "sạc" in name.lower():
        set_if_empty(specs, "accessory_type", "Thiết bị sạc")
        set_if_empty(specs, "ports", pick(specs, "Số cổng", "Số cổng sạc", "Cổng kết nối"))
        set_if_empty(specs, "charging_standard", pick(specs, "Chuẩn sạc", "Hỗ trợ chuẩn sạc") or "USB Power Delivery")
    elif "chuột" in name.lower():
        set_if_empty(specs, "accessory_type", "Chuột gaming")
        set_if_empty(specs, "connectivity", pick(specs, "Kết nối"))
    elif "bàn phím" in name.lower():
        set_if_empty(specs, "accessory_type", "Bàn phím cơ")
        set_if_empty(specs, "connectivity", pick(specs, "Kết nối"))
    else:
        set_if_empty(specs, "accessory_type", subcategory or "Phụ kiện công nghệ")
    set_if_empty(specs, "compatibility", pick(specs, "Khả năng tương thích") or "Thiết bị hỗ trợ chuẩn kết nối tương ứng")
    set_if_empty(specs, "material", pick(specs, "Chất liệu", "Chất liệu vỏ", "Chất liệu đầu cáp"))


def normalize_product(row: asyncpg.Record) -> dict:
    specs = as_dict(row["specifications"])
    category = (row["category"] or "").lower()
    name = row["name"]
    brand = row["brand"]
    subcategory = row["subcategory"]
    if "điện thoại" in category:
        normalize_phone(specs, name, brand)
    elif "máy tính bảng" in category:
        normalize_tablet(specs, name, brand)
    elif "đồng hồ" in category:
        normalize_wearable(specs, name, brand)
    elif category == "camera":
        normalize_camera(specs, name)
    elif "máy ảnh" in category:
        normalize_camera_photo(specs)
    elif "máy tính xách tay" in category:
        normalize_laptop(specs, name, brand)
    elif "phụ kiện" in category:
        normalize_accessory(specs, name, subcategory)
    for key, value in PRODUCT_SPEC_OVERRIDES.get(row["sku"], {}).items():
        set_if_empty(specs, key, value)
    return specs


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT p.id, p.sku, p.name, b.name AS brand, c.name AS category, sc.name AS subcategory, p.specifications
            FROM products p
            LEFT JOIN brands b ON b.id = p.brand_id
            LEFT JOIN categories c ON c.id = p.category_id
            LEFT JOIN categories sc ON sc.id = p.subcategory_id
            WHERE p.deleted_at IS NULL
              AND p.parent_product_id IS NULL
              AND p.status IN ('ACTIVE', 'DRAFT')
            ORDER BY p.name
            """
        )
        updated = 0
        for row in rows:
            before = as_dict(row["specifications"])
            after = normalize_product(row)
            if after != before:
                await conn.execute(
                    """
                    UPDATE products
                    SET specifications = $1::jsonb,
                        updated_at = NOW()
                    WHERE id = $2
                    """,
                    json.dumps(after, ensure_ascii=False),
                    row["id"],
                )
                updated += 1
                print(f"{row['sku']} | {row['name']}: {len(before)} -> {len(after)} thông số")
        print(f"Đã chuẩn hóa thông số cho {updated} sản phẩm.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
