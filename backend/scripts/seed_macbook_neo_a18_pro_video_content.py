import asyncio
from uuid import uuid4

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
PRODUCT_SKU = "MBNEOA18P"
VIDEO_TITLE = "MacBook Neo 13 inch A18 Pro 2026 - Gọn nhẹ, mới mẻ, sẵn sàng cho mỗi ngày"

DESCRIPTION = (
    "Nội dung nháp cho video giới thiệu MacBook Neo 13 inch A18 Pro 2026: tập trung vào thiết kế trẻ trung, "
    "chip A18 Pro, màn hình 13 inch, thời lượng pin dài và trải nghiệm học tập, văn phòng linh hoạt."
)

CONTENT_BODY = """MacBook Neo 13 inch A18 Pro 2026 hướng đến người dùng cần một chiếc MacBook nhỏ gọn, hiện đại và dễ mang theo cho học tập, làm việc, giải trí hằng ngày.

Gợi ý kịch bản video:
1. Mở đầu bằng cảnh đặt máy trong balo, cầm một tay hoặc mở máy nhanh trên bàn làm việc để nhấn mạnh thiết kế 13 inch gọn nhẹ, trẻ trung.
2. Chuyển qua màn hình Liquid Retina 13 inch khi mở tài liệu, xem ảnh, duyệt web và học online để thể hiện không gian hiển thị rõ, màu sắc dễ nhìn.
3. Giới thiệu chip Apple A18 Pro cho các tác vụ quen thuộc: làm slide, xử lý bảng tính, gọi video, mở nhiều tab, chỉnh ảnh nhẹ và giải trí sau giờ học/làm.
4. Nhấn vào thời lượng pin dài, máy chạy êm, bàn phím Magic Keyboard với Touch ID và kết nối Wi-Fi 6E để phù hợp nhịp dùng linh hoạt cả ngày.
5. Kết video bằng thông điệp: MacBook Neo 13 inch A18 Pro 2026 là lựa chọn đáng chú ý cho người muốn một chiếc laptop Apple nhỏ gọn, dễ dùng và có cấu hình đủ mạnh cho nhu cầu thường nhật.

Caption đề xuất:
MacBook Neo 13 inch A18 Pro 2026 - gọn nhẹ, màu sắc trẻ trung, chip A18 Pro mượt mà cho học tập, văn phòng và giải trí mỗi ngày.
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

        existing = await conn.fetchrow(
            """
            SELECT id
            FROM videos
            WHERE title = $1
              AND content_type = 'VIDEO'
              AND deleted_at IS NULL
            """,
            VIDEO_TITLE,
        )

        if existing:
            video_id = existing["id"]
            await conn.execute(
                """
                UPDATE videos
                SET description = $1,
                    content_body = $2,
                    thumbnail_url = $3,
                    cta_label = 'Xem MacBook Neo',
                    cta_url = $4,
                    video_source = 'UPLOAD',
                    video_category = 'PRODUCT',
                    status = 'DRAFT',
                    is_active = FALSE,
                    video_url = NULL,
                    version = version + 1,
                    updated_at = NOW()
                WHERE id = $5
                """,
                DESCRIPTION,
                CONTENT_BODY,
                product["image_url"],
                f"/product/{product['id']}",
                video_id,
            )
        else:
            video_id = uuid4()
            await conn.execute(
                """
                INSERT INTO videos (
                    id, title, description, content_type, video_source, video_category,
                    status, video_url, thumbnail_url, content_body, cta_label, cta_url,
                    like_count, view_count, sort_order, is_active, version, created_at, updated_at
                )
                VALUES (
                    $1, $2, $3, 'VIDEO', 'UPLOAD', 'PRODUCT',
                    'DRAFT', NULL, $4, $5, 'Xem MacBook Neo', $6,
                    0, 0, 0, FALSE, 1, NOW(), NOW()
                )
                """,
                video_id,
                VIDEO_TITLE,
                DESCRIPTION,
                product["image_url"],
                CONTENT_BODY,
                f"/product/{product['id']}",
            )

        await conn.execute(
            """
            INSERT INTO content_product_relations (content_id, product_id)
            VALUES ($1, $2)
            ON CONFLICT (content_id, product_id) DO NOTHING
            """,
            video_id,
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
                video_id,
                category_id,
            )

        print(f"Prepared draft video content for {product['name']}: {video_id}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
