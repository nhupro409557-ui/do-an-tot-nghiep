import asyncio
import sys
from pathlib import Path

import asyncpg

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings


SUPPLIERS = [
    {
        "code": "NCC-APPLE-VN",
        "name": "Công ty TNHH Phân phối Apple Việt Nam",
        "contact_name": "Nguyễn Minh Anh",
        "phone": "0901 234 567",
        "email": "apple.vn@example.com",
        "address": "Tầng 12, 72 Lê Thánh Tôn, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
        "tax_code": "0312345678",
        "website": "https://apple.example.vn",
        "note": "Nhà cung cấp nhóm iPhone, iPad, MacBook, Apple Watch và phụ kiện Apple.",
        "is_active": True,
    },
    {
        "code": "NCC-SAMSUNG-VN",
        "name": "Công ty Cổ phần Samsung Electronics Việt Nam",
        "contact_name": "Trần Quốc Bảo",
        "phone": "0902 345 678",
        "email": "samsung.vn@example.com",
        "address": "Tòa nhà Capital Place, 29 Liễu Giai, Quận Ba Đình, Hà Nội",
        "tax_code": "0102345678",
        "website": "https://samsung.example.vn",
        "note": "Nhà cung cấp điện thoại, máy tính bảng, đồng hồ và thiết bị Samsung.",
        "is_active": True,
    },
    {
        "code": "NCC-OPPO-VN",
        "name": "Công ty TNHH OPPO Việt Nam",
        "contact_name": "Lê Hoàng Nam",
        "phone": "0903 456 789",
        "email": "oppo.vn@example.com",
        "address": "Tầng 8, 194 Golden Building, 473 Điện Biên Phủ, Quận Bình Thạnh, TP. Hồ Chí Minh",
        "tax_code": "0313456789",
        "website": "https://oppo.example.vn",
        "note": "Nhà cung cấp điện thoại OPPO, phụ kiện và linh kiện bảo hành.",
        "is_active": True,
    },
    {
        "code": "NCC-PHUKIEN-GIAKHANG",
        "name": "Công ty TNHH Phụ kiện Gia Khang",
        "contact_name": "Phạm Thùy Dương",
        "phone": "0904 567 890",
        "email": "kinhdoanh@giakhang.example.vn",
        "address": "118 Nguyễn Văn Linh, Phường Tân Thuận Tây, Quận 7, TP. Hồ Chí Minh",
        "tax_code": "0314567890",
        "website": "https://giakhang.example.vn",
        "note": "Nhà cung cấp sạc, cáp, tai nghe, bao da và phụ kiện phổ thông.",
        "is_active": True,
    },
    {
        "code": "NCC-CAMERA-MINHQUANG",
        "name": "Công ty Cổ phần Thiết bị số Minh Quang",
        "contact_name": "Vũ Thanh Tùng",
        "phone": "0905 678 901",
        "email": "sales@minhquang.example.vn",
        "address": "25 Nguyễn Thị Minh Khai, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
        "tax_code": "0315678901",
        "website": "https://minhquang.example.vn",
        "note": "Nhà cung cấp camera, máy ảnh, thiết bị quay phim và phụ kiện hình ảnh.",
        "is_active": True,
    },
]


async def main() -> None:
    db_url = settings.database_url
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    conn = await asyncpg.connect(db_url)
    try:
        await conn.executemany(
            """
            INSERT INTO suppliers (
                code, name, contact_name, phone, email, address, tax_code, website, note, is_active
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
            )
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                contact_name = EXCLUDED.contact_name,
                phone = EXCLUDED.phone,
                email = EXCLUDED.email,
                address = EXCLUDED.address,
                tax_code = EXCLUDED.tax_code,
                website = EXCLUDED.website,
                note = EXCLUDED.note,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
            """,
            [
                (
                    supplier["code"],
                    supplier["name"],
                    supplier["contact_name"],
                    supplier["phone"],
                    supplier["email"],
                    supplier["address"],
                    supplier["tax_code"],
                    supplier["website"],
                    supplier["note"],
                    supplier["is_active"],
                )
                for supplier in SUPPLIERS
            ],
        )

        rows = await conn.fetch(
            """
            SELECT code, name, contact_name, phone, is_active
            FROM suppliers
            WHERE code = ANY($1::text[])
            ORDER BY code
            """,
            [supplier["code"] for supplier in SUPPLIERS],
        )
        print(f"Đã seed {len(rows)} nhà cung cấp:")
        for row in rows:
            status = "đang hoạt động" if row["is_active"] else "đã ẩn"
            print(f"- {row['code']}: {row['name']} ({row['contact_name']}, {row['phone']}) - {status}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
