from __future__ import annotations

import asyncio
import json
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


SEED_OWNER = "electromart-extended-warranty-2026-05-23"


def tier(min_amount: int, max_amount: int | None, price: int) -> dict:
    return {"min": min_amount, "max": max_amount, "price": price}


MOBILE_TABLE = [
    (0, 2_500_000, 150_000, 200_000, 250_000, 150_000),
    (2_500_001, 4_000_000, 180_000, 250_000, 350_000, 180_000),
    (4_000_001, 5_000_000, 200_000, 300_000, 450_000, 250_000),
    (5_000_001, 6_500_000, 300_000, 400_000, 550_000, 320_000),
    (6_500_001, 7_500_000, 350_000, 450_000, 600_000, 400_000),
    (7_500_001, 8_500_000, 400_000, 550_000, 700_000, 450_000),
    (8_500_001, 10_000_000, 450_000, 600_000, 800_000, 500_000),
    (10_000_001, 12_000_000, 500_000, 750_000, 1_000_000, 600_000),
    (12_000_001, 14_000_000, 600_000, 850_000, 1_100_000, 700_000),
    (14_000_001, 16_000_000, 700_000, 1_000_000, 1_300_000, 800_000),
    (16_000_001, 18_000_000, 800_000, 1_100_000, 1_400_000, 900_000),
    (18_000_001, 20_000_000, 900_000, 1_200_000, 1_500_000, 1_000_000),
    (20_000_001, 25_000_000, 1_100_000, 1_400_000, 1_800_000, 1_200_000),
    (25_000_001, 30_000_000, 1_200_000, 1_600_000, 2_000_000, 1_400_000),
    (30_000_001, 40_000_000, 1_300_000, 1_800_000, 2_400_000, 1_600_000),
    (40_000_001, 50_000_000, 1_500_000, 2_200_000, 3_000_000, 2_000_000),
    (50_000_001, 60_000_000, 1_800_000, 2_500_000, 3_500_000, 2_200_000),
]

LAPTOP_TABLE = [
    (0, 10_000_000, 700_000, 700_000, 1_400_000),
    (10_000_001, 15_000_000, 1_000_000, 1_000_000, 1_800_000),
    (15_000_001, 20_000_000, 1_500_000, 1_400_000, 2_300_000),
    (20_000_001, 25_000_000, 1_800_000, 1_800_000, 2_800_000),
    (25_000_001, 30_000_000, 2_200_000, 2_200_000, 3_400_000),
    (30_000_001, 35_000_000, 2_600_000, 2_600_000, 3_800_000),
    (35_000_001, 40_000_000, 3_000_000, 3_000_000, 4_000_000),
    (45_000_001, 100_000_000, 4_000_000, 4_000_000, 5_000_000),
]

ACCESSORY_TABLE = [
    (0, 1_000_000, 100_000, 100_000),
    (1_000_001, 2_000_000, 200_000, 100_000),
    (2_000_001, 3_000_000, 300_000, 150_000),
    (3_000_001, 4_000_000, 400_000, 200_000),
    (4_000_001, 5_000_000, 400_000, 300_000),
    (5_000_001, 8_000_000, 600_000, 400_000),
    (8_000_001, 10_000_000, 800_000, 500_000),
    (10_000_001, 15_000_000, 1_000_000, 650_000),
    (15_000_001, 20_000_000, 1_400_000, 800_000),
    (20_000_001, 30_000_000, 2_000_000, 1_000_000),
    (30_000_001, 40_000_000, 2_000_000, 1_200_000),
]

TV_TABLE = [
    (3_000_000, 5_000_000, 300_000),
    (5_000_001, 7_000_000, 400_000),
    (7_000_001, 10_000_000, 500_000),
    (10_000_001, 12_000_000, 600_000),
    (12_000_001, 14_000_000, 700_000),
    (14_000_001, 16_000_000, 800_000),
    (16_000_001, 18_000_000, 900_000),
    (18_000_001, 20_000_000, 1_000_000),
    (20_000_001, 22_000_000, 1_100_000),
    (22_000_001, 25_000_000, 1_300_000),
    (25_000_001, 30_000_000, 1_500_000),
    (30_000_001, 40_000_000, 2_000_000),
    (40_000_001, 50_000_000, 2_500_000),
    (50_000_001, 60_000_000, 3_000_000),
    (60_000_001, 70_000_000, 3_500_000),
    (70_000_001, 80_000_000, 4_000_000),
    (80_000_001, 100_000_000, 5_000_000),
]


def service(
    code: str,
    name: str,
    attribute_group: str,
    duration_months: int,
    tiers: list[dict],
    applies_to: list[str],
    *,
    processing_time: str,
    benefits: list[str],
    exclusions: list[str],
    support_limit: str | None = None,
) -> dict:
    return {
        "code": code,
        "name": name,
        "service_type": "PRODUCT_SERVICE",
        "attribute_group": attribute_group,
        "duration_months": duration_months,
        "price_mode": "TIERED_AMOUNT",
        "fixed_price": 0,
        "percent_value": 0,
        "base_amount": 0,
        "metadata": {
            "seedOwner": SEED_OWNER,
            "policyName": "Chính sách bảo hành mở rộng ElectroMart Việt Nam",
            "appliesTo": applies_to,
            "bindsToImei": True,
            "priceTiers": tiers,
            "processingTime": processing_time,
            "benefits": benefits,
            "exclusions": exclusions,
            "supportLimit": support_limit,
            "refundRule": {"withinDays": 7, "refundPercent": 50, "requiresUnused": True},
            "transferable": True,
        },
    }


def fixed_support(code: str, name: str, group: str, price: int, applies_to: list[str], metadata: dict | None = None) -> dict:
    return {
        "code": code,
        "name": name,
        "service_type": "SUPPORT_SERVICE",
        "attribute_group": group,
        "duration_months": 0,
        "price_mode": "FIXED",
        "fixed_price": price,
        "percent_value": 0,
        "base_amount": 0,
        "metadata": {"seedOwner": SEED_OWNER, "appliesTo": applies_to, **(metadata or {})},
    }


SERVICES = [
    service(
        "VIP-1D1-MOBILE-6M",
        "Bảo hành 1 đổi 1 VIP điện thoại/máy tính bảng 6 tháng",
        "ONE_FOR_ONE",
        6,
        [tier(row[0], row[1], row[2]) for row in MOBILE_TABLE],
        ["phone_new", "phone_used", "tablet_new", "tablet_used"],
        processing_time="24 giờ đến tối đa 14 ngày làm việc",
        benefits=["Đổi sản phẩm tương đương khi lỗi phần cứng do nhà sản xuất", "Không giới hạn số lần xử lý nếu đáp ứng điều kiện"],
        exclusions=["Rơi vỡ", "Vào nước", "Cấn móp, cong vênh", "Tự ý sửa chữa", "Mất hoặc sai IMEI/Serial"],
    ),
    service(
        "VIP-1D1-MOBILE-12M",
        "Bảo hành 1 đổi 1 VIP điện thoại/máy tính bảng 12 tháng",
        "ONE_FOR_ONE",
        12,
        [tier(row[0], row[1], row[3]) for row in MOBILE_TABLE],
        ["phone_new", "phone_used", "tablet_new", "tablet_used"],
        processing_time="24 giờ đến tối đa 14 ngày làm việc",
        benefits=["Đổi sản phẩm tương đương khi lỗi phần cứng do nhà sản xuất", "Có thể chuyển nhượng cùng sản phẩm nếu còn hiệu lực"],
        exclusions=["Rơi vỡ", "Vào nước", "Cấn móp, cong vênh", "Tự ý sửa chữa", "Mất hoặc sai IMEI/Serial"],
    ),
    service(
        "RVVN-MOBILE-12M",
        "Bảo hành rơi vỡ - rơi nước điện thoại/máy tính bảng 12 tháng",
        "ACCIDENTAL_DAMAGE",
        12,
        [tier(row[0], row[1], row[4]) for row in MOBILE_TABLE],
        ["phone_new", "phone_used", "tablet_new", "tablet_used"],
        processing_time="7 đến 14 ngày làm việc",
        benefits=["Hỗ trợ chi phí sửa chữa khi rơi vỡ, vào nước hoặc tác động ngoại lực", "Hỗ trợ tối đa 90% chi phí sửa chữa"],
        exclusions=["Mất máy", "Không xác định được IMEI/Serial", "Cố ý phá hoại", "Đã sửa chữa tại đơn vị không ủy quyền"],
        support_limit="Tối đa 90% chi phí sửa chữa, không vượt quá giới hạn bảo hành của sản phẩm",
    ),
    service(
        "S24-MOBILE-12M",
        "Bảo hành mở rộng S24+ điện thoại/máy tính bảng 12 tháng",
        "EXTENDED_WARRANTY",
        12,
        [tier(row[0], row[1], row[5]) for row in MOBILE_TABLE],
        ["phone_new", "tablet_new"],
        processing_time="7 đến 14 ngày làm việc",
        benefits=["Gia hạn bảo hành lỗi nhà sản xuất sau bảo hành chính hãng", "Miễn phí sửa chữa và thay linh kiện nếu thuộc phạm vi bảo hành"],
        exclusions=["Sản phẩm đã qua sử dụng không áp dụng mặc định", "Rơi vỡ", "Vào nước", "Cháy nổ", "Tự ý sửa chữa"],
    ),
    service(
        "VIP-1D1-LAPTOP-12M",
        "Bảo hành 1 đổi 1 VIP laptop/MacBook 12 tháng",
        "ONE_FOR_ONE",
        12,
        [tier(row[0], row[1], row[2]) for row in LAPTOP_TABLE],
        ["laptop", "macbook"],
        processing_time="24 giờ đến tối đa 14 ngày làm việc",
        benefits=["Đổi sản phẩm tương đương khi lỗi phần cứng do nhà sản xuất"],
        exclusions=["Rơi vỡ", "Vào nước", "Cấn móp, cong vênh", "Tự ý sửa chữa", "Mất hoặc sai serial"],
    ),
    service(
        "S24-LAPTOP-12M",
        "Bảo hành mở rộng S24+ laptop/MacBook 12 tháng",
        "EXTENDED_WARRANTY",
        12,
        [tier(row[0], row[1], row[3]) for row in LAPTOP_TABLE],
        ["laptop", "macbook"],
        processing_time="7 đến 14 ngày làm việc; MacBook có thể 3 đến 4 tuần",
        benefits=["Gia hạn bảo hành lỗi nhà sản xuất sau bảo hành chính hãng", "Miễn phí sửa chữa và thay linh kiện nếu thuộc phạm vi bảo hành"],
        exclusions=["Rơi vỡ", "Vào nước", "Cháy nổ", "Biến dạng", "Tự ý sửa chữa"],
    ),
    service(
        "S24-LAPTOP-24M",
        "Bảo hành mở rộng S24+ laptop/MacBook 24 tháng",
        "EXTENDED_WARRANTY",
        24,
        [tier(row[0], row[1], row[4]) for row in LAPTOP_TABLE],
        ["laptop", "macbook"],
        processing_time="7 đến 14 ngày làm việc; MacBook có thể 3 đến 4 tuần",
        benefits=["Gia hạn bảo hành lỗi nhà sản xuất sau bảo hành chính hãng", "Miễn phí sửa chữa và thay linh kiện nếu thuộc phạm vi bảo hành"],
        exclusions=["Rơi vỡ", "Vào nước", "Cháy nổ", "Biến dạng", "Tự ý sửa chữa"],
    ),
    service(
        "VIP-1D1-ACCESSORY-12M",
        "Bảo hành 1 đổi 1 VIP phụ kiện cao cấp 12 tháng",
        "ONE_FOR_ONE",
        12,
        [tier(row[0], row[1], row[2]) for row in ACCESSORY_TABLE],
        ["premium_accessory", "premium_headphone", "smartwatch"],
        processing_time="24 giờ đến tối đa 14 ngày làm việc",
        benefits=["Đổi sản phẩm tương đương khi lỗi phần cứng do nhà sản xuất"],
        exclusions=["Rơi vỡ", "Vào nước", "Tự ý sửa chữa", "Mất serial"],
    ),
    service(
        "S24-ACCESSORY-12M",
        "Bảo hành mở rộng S24+ phụ kiện cao cấp 12 tháng",
        "EXTENDED_WARRANTY",
        12,
        [tier(row[0], row[1], row[3]) for row in ACCESSORY_TABLE],
        ["premium_accessory"],
        processing_time="7 đến 14 ngày làm việc",
        benefits=["Gia hạn bảo hành lỗi nhà sản xuất sau bảo hành tiêu chuẩn"],
        exclusions=["Rơi vỡ", "Vào nước", "Tự ý sửa chữa", "Mất serial"],
    ),
    service(
        "VIP-1D1-TV-12M",
        "Bảo hành 1 đổi 1 VIP Tivi 12 tháng",
        "ONE_FOR_ONE",
        12,
        [tier(row[0], row[1], row[2]) for row in TV_TABLE],
        ["tv"],
        processing_time="24 giờ đến tối đa 14 ngày làm việc",
        benefits=["Đổi sản phẩm tương đương khi lỗi phần cứng do nhà sản xuất"],
        exclusions=["Rơi vỡ", "Vào nước", "Cháy nổ", "Tự ý sửa chữa", "Mất serial"],
    ),
    fixed_support("SCREEN-PHONE-BASIC", "Dán kính cường lực điện thoại cơ bản", "INSTALLATION", 50_000, ["phone"]),
    fixed_support("SCREEN-PHONE-PREMIUM", "Dán kính cường lực điện thoại cao cấp", "INSTALLATION", 150_000, ["phone"]),
    fixed_support("DATA-PHONE-FULL", "Sao lưu và chuyển dữ liệu điện thoại trọn gói", "SUPPORT", 150_000, ["phone", "tablet"]),
    fixed_support("SETUP-LAPTOP-BASIC", "Cài đặt laptop cơ bản", "SUPPORT", 200_000, ["laptop"]),
    fixed_support("SETUP-LAPTOP-PRO", "Cài đặt laptop nâng cao và tối ưu hiệu năng", "SUPPORT", 350_000, ["laptop"]),
    fixed_support("INSTALL-SSD-RAM", "Lắp đặt SSD/RAM và kiểm tra laptop", "INSTALLATION", 180_000, ["laptop", "pc"]),
    fixed_support("CLEAN-PHONE-TABLET", "Vệ sinh điện thoại/máy tính bảng", "CLEANING", 80_000, ["phone", "tablet"]),
    fixed_support("CLEAN-LAPTOP-BASIC", "Vệ sinh laptop cơ bản", "CLEANING", 150_000, ["laptop"]),
    fixed_support("CLEAN-LAPTOP-PRO", "Vệ sinh laptop và thay keo tản nhiệt", "CLEANING", 250_000, ["laptop"]),
    fixed_support("INSTALL-PRINTER-WIFI", "Lắp đặt máy in/Wi-Fi tại nhà", "INSTALLATION", 250_000, ["printer", "network"], {"onsite": True}),
    fixed_support("ONSITE-SUPPORT-1H", "Hỗ trợ kỹ thuật tại nhà 1 giờ", "SUPPORT", 300_000, ["phone", "tablet", "laptop", "pc"], {"onsite": True, "durationMinutes": 60}),
    fixed_support("ONSITE-LAPTOP-SETUP", "Cài đặt và bàn giao laptop tại nhà", "INSTALLATION", 400_000, ["laptop"], {"onsite": True}),
]

OLD_SEED_CODES = {
    "BHMR-PHONE-6M",
    "BHMR-PHONE-12M",
    "BHMR-PHONE-24M",
    "BHMR-LAPTOP-6M",
    "BHMR-LAPTOP-12M",
    "BHMR-LAPTOP-24M",
    "VIP-1D1-PHONE-6M",
    "VIP-1D1-PHONE-12M",
    "VIP-1D1-LAPTOP-6M",
    "VIP-1D1-LAPTOP-12M",
    "RVVN-PHONE-12M",
    "RVVN-LAPTOP-12M",
    "SETUP-PHONE-DATA",
}

OLD_SERVICE_NAMES = {
    "BHMR-PHONE-6M": "Bảo hành mở rộng điện thoại 6 tháng",
    "BHMR-PHONE-12M": "Bảo hành mở rộng điện thoại 12 tháng",
    "BHMR-PHONE-24M": "Bảo hành mở rộng điện thoại 24 tháng",
    "BHMR-LAPTOP-6M": "Bảo hành mở rộng laptop 6 tháng",
    "BHMR-LAPTOP-12M": "Bảo hành mở rộng laptop 12 tháng",
    "BHMR-LAPTOP-24M": "Bảo hành mở rộng laptop 24 tháng",
    "VIP-1D1-PHONE-6M": "VIP 1 đổi 1 điện thoại 6 tháng",
    "VIP-1D1-PHONE-12M": "VIP 1 đổi 1 điện thoại 12 tháng",
    "VIP-1D1-LAPTOP-6M": "VIP 1 đổi 1 laptop 6 tháng",
    "VIP-1D1-LAPTOP-12M": "Bảo hành 1 đổi 1 VIP laptop/MacBook 12 tháng",
    "RVVN-PHONE-12M": "Bảo vệ rơi vỡ vào nước điện thoại 12 tháng",
    "RVVN-LAPTOP-12M": "Bảo vệ rơi vỡ vào nước laptop 12 tháng",
    "SETUP-PHONE-DATA": "Cài đặt và chuyển dữ liệu điện thoại",
}


async def main() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    service_codes = [service["code"] for service in SERVICES]
    async with engine.begin() as conn:
        for item in SERVICES:
            await conn.execute(
                text(
                    """
                    INSERT INTO attached_services (
                        id, code, name, service_type, attribute_group, duration_months,
                        price_mode, fixed_price, percent_value, base_amount, is_active, metadata
                    )
                    VALUES (
                        :id, :code, :name, :service_type, :attribute_group, :duration_months,
                        :price_mode, :fixed_price, :percent_value, :base_amount, TRUE, CAST(:metadata AS jsonb)
                    )
                    ON CONFLICT (code) DO UPDATE SET
                        name = EXCLUDED.name,
                        service_type = EXCLUDED.service_type,
                        attribute_group = EXCLUDED.attribute_group,
                        duration_months = EXCLUDED.duration_months,
                        price_mode = EXCLUDED.price_mode,
                        fixed_price = EXCLUDED.fixed_price,
                        percent_value = EXCLUDED.percent_value,
                        base_amount = EXCLUDED.base_amount,
                        is_active = TRUE,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """
                ),
                {**item, "id": uuid4(), "metadata": json.dumps(item["metadata"], ensure_ascii=False)},
            )
        await conn.execute(
            text(
                """
                UPDATE attached_services
                SET is_active = FALSE, updated_at = NOW()
                WHERE code = ANY(:old_codes)
                  AND code <> ALL(:service_codes)
                """
            ),
            {"old_codes": list(OLD_SEED_CODES), "service_codes": service_codes},
        )
        for code, name in OLD_SERVICE_NAMES.items():
            await conn.execute(
                text("UPDATE attached_services SET name = :name, updated_at = NOW() WHERE code = :code"),
                {"code": code, "name": name},
            )
    await engine.dispose()
    print(f"Seeded {len(SERVICES)} attached services from ElectroMart extended warranty policy.")


if __name__ == "__main__":
    asyncio.run(main())
