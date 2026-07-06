import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:anhnhu057@localhost:5432/postgres",
)


LOCATION_RENAMES = [
    {
        "old_code": "QC-01",
        "new_code": "CL-01-01",
        "name": "Dãy cách ly - Kệ 01 - Ô 01",
        "zone": "Dãy cách ly",
        "purpose": "QC",
        "sort_order": 850101,
        "description": "Kệ cách ly hàng chờ kiểm tra hoặc chưa đạt QC.",
    },
    {
        "old_code": "BH-01",
        "new_code": "BH-01-01",
        "name": "Dãy bảo hành - Kệ 01 - Ô 01",
        "zone": "Dãy bảo hành",
        "purpose": "WARRANTY",
        "sort_order": 910101,
        "description": "Kệ lưu hàng gửi hoặc nhận bảo hành.",
    },
    {
        "old_code": "ERR-01",
        "new_code": "ERR-01-01",
        "name": "Dãy hàng lỗi - Kệ 01 - Ô 01",
        "zone": "Dãy hàng lỗi",
        "purpose": "DAMAGED",
        "sort_order": 920101,
        "description": "Kệ lưu hàng lỗi chờ xử lý.",
    },
    {
        "old_code": "RT-01",
        "new_code": "RT-01-01",
        "name": "Dãy hàng trả - Kệ 01 - Ô 01",
        "zone": "Dãy hàng trả",
        "purpose": "RETURN",
        "sort_order": 930101,
        "description": "Kệ lưu hàng khách trả chờ kiểm tra.",
    },
]


async def main() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                UPDATE inventory_locations
                SET name = 'Kho',
                    zone = 'Kho',
                    purpose = 'VIRTUAL',
                    sort_order = 0,
                    length_cm = NULL,
                    width_cm = NULL,
                    height_cm = NULL,
                    updated_at = NOW()
                WHERE code = 'MAIN'
                """
            )
        )

        for item in LOCATION_RENAMES:
            target = await conn.execute(
                text("SELECT id FROM inventory_locations WHERE code = :code"),
                {"code": item["new_code"]},
            )
            old = await conn.execute(
                text("SELECT id FROM inventory_locations WHERE code = :code"),
                {"code": item["old_code"]},
            )
            target_id = target.scalar_one_or_none()
            old_id = old.scalar_one_or_none()
            if target_id and old_id and target_id != old_id:
                raise RuntimeError(
                    f"Không thể đổi {item['old_code']} sang {item['new_code']}: mã mới đã tồn tại."
                )
            if old_id:
                await conn.execute(
                    text(
                        """
                        UPDATE inventory_locations
                        SET code = :new_code,
                            name = :name,
                            zone = :zone,
                            purpose = :purpose,
                            sort_order = :sort_order,
                            description = :description,
                            length_cm = COALESCE(length_cm, 100),
                            width_cm = COALESCE(width_cm, 60),
                            height_cm = COALESCE(height_cm, 40),
                            usable_ratio = COALESCE(usable_ratio, 0.75),
                            status = 'ACTIVE',
                            updated_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {**item, "id": old_id},
                )
            elif not target_id:
                await conn.execute(
                    text(
                        """
                        INSERT INTO inventory_locations (
                            code, name, location_type, status, is_default, zone,
                            description, purpose, sort_order, allow_mixed_sku,
                            length_cm, width_cm, height_cm, usable_ratio
                        )
                        VALUES (
                            :new_code, :name, 'WAREHOUSE', 'ACTIVE', FALSE, :zone,
                            :description, :purpose, :sort_order, TRUE,
                            100, 60, 40, 0.75
                        )
                        """
                    ),
                    item,
                )
            else:
                await conn.execute(
                    text(
                        """
                        UPDATE inventory_locations
                        SET name = :name,
                            zone = :zone,
                            purpose = :purpose,
                            sort_order = :sort_order,
                            description = :description,
                            length_cm = COALESCE(length_cm, 100),
                            width_cm = COALESCE(width_cm, 60),
                            height_cm = COALESCE(height_cm, 40),
                            usable_ratio = COALESCE(usable_ratio, 0.75),
                            status = 'ACTIVE',
                            updated_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {**item, "id": target_id},
                )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
