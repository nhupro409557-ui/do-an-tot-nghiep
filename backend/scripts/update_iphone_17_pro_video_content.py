import asyncio

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
PRODUCT_SKU = "IP17P"
VIDEO_TITLE_MATCH = "iphone 17 pro"

TITLE = "iPhone 17 Pro - Sức mạnh Pro trong thiết kế mới"
DESCRIPTION = (
    "Nội dung giới thiệu iPhone 17 Pro: thiết kế cao cấp, hiệu năng mạnh, "
    "camera Pro và trải nghiệm màn hình mượt cho công việc lẫn giải trí."
)
CONTENT_BODY = """iPhone 17 Pro hướng đến người dùng cần một chiếc iPhone mạnh mẽ, cao cấp và bền bỉ cho nhiều nhu cầu trong ngày.

Gợi ý kịch bản video:
1. Mở đầu bằng cảnh cận máy, nhấn mạnh thiết kế Pro, mặt lưng sang và cụm camera nổi bật.
2. Chuyển qua màn hình với thao tác vuốt, xem ảnh, xem video để thể hiện độ mượt và chất lượng hiển thị.
3. Giới thiệu hiệu năng mạnh cho làm việc, chơi game, chỉnh ảnh, quay video và xử lý tác vụ nặng.
4. Nhấn vào hệ thống camera Pro: chụp chi tiết tốt, màu sắc ổn định, hỗ trợ quay video chất lượng cao.
5. Kết video bằng thông điệp: iPhone 17 Pro phù hợp với người muốn một chiếc máy gọn hơn Pro Max nhưng vẫn có trải nghiệm Pro đầy đủ.

Caption đề xuất:
iPhone 17 Pro - thiết kế sang, hiệu năng mạnh, camera Pro và trải nghiệm mượt mà cho người dùng cần một chiếc iPhone cao cấp để dùng lâu dài.
"""


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        product = await conn.fetchrow(
            """
            SELECT id, name, image_url, category_id, subcategory_id
            FROM products
            WHERE sku = $1 AND deleted_at IS NULL
            """,
            PRODUCT_SKU,
        )
        if not product:
            print(f"Product {PRODUCT_SKU} not found.")
            return

        video = await conn.fetchrow(
            """
            SELECT id, title
            FROM videos
            WHERE deleted_at IS NULL
              AND content_type = 'VIDEO'
              AND LOWER(title) LIKE '%' || $1 || '%'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            VIDEO_TITLE_MATCH,
        )
        if not video:
            print("iPhone 17 Pro video not found.")
            return

        await conn.execute(
            """
            UPDATE videos
            SET title = $1,
                description = $2,
                content_body = $3,
                thumbnail_url = COALESCE(NULLIF(thumbnail_url, ''), $4),
                cta_label = 'Xem iPhone 17 Pro',
                cta_url = $5,
                video_category = 'PRODUCT',
                updated_at = NOW(),
                version = version + 1
            WHERE id = $6
            """,
            TITLE,
            DESCRIPTION,
            CONTENT_BODY,
            product["image_url"],
            f"/product/{product['id']}",
            video["id"],
        )

        await conn.execute(
            """
            INSERT INTO content_product_relations (content_id, product_id)
            VALUES ($1, $2)
            ON CONFLICT (content_id, product_id) DO NOTHING
            """,
            video["id"],
            product["id"],
        )

        for category_id in [product["subcategory_id"], product["category_id"]]:
            if not category_id:
                continue
            await conn.execute(
                """
                INSERT INTO content_category_relations (content_id, category_id)
                VALUES ($1, $2)
                ON CONFLICT (content_id, category_id) DO NOTHING
                """,
                video["id"],
                category_id,
            )

        print(f"Updated video content for {product['name']}: {video['id']}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
