import asyncio
from uuid import uuid4

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
PRODUCT_SKU = "MBAIRM3"
VIDEO_TITLE = "MacBook Air M3 13 inch - Mỏng nhẹ, pin lâu, làm việc mượt mỗi ngày"

DESCRIPTION = (
    "Nội dung nháp cho video giới thiệu MacBook Air M3 13 inch: tập trung vào thiết kế mỏng nhẹ, "
    "chip M3 mạnh mẽ, màn hình Liquid Retina đẹp và thời lượng pin dài cho học tập, văn phòng, sáng tạo nhẹ."
)

CONTENT_BODY = """MacBook Air M3 13 inch phù hợp với người dùng cần một chiếc laptop gọn nhẹ, bền bỉ và đủ mạnh để làm việc, học tập, giải trí mỗi ngày.

Gợi ý kịch bản video:
1. Mở đầu bằng cảnh cầm máy một tay, đặt vào balo hoặc trên bàn làm việc để nhấn mạnh thân máy mỏng nhẹ, dễ mang theo.
2. Chuyển sang màn hình Liquid Retina 13.6 inch khi mở tài liệu, duyệt web, xem ảnh và video để thể hiện màu sắc sáng rõ, không gian hiển thị thoải mái.
3. Giới thiệu chip Apple M3 qua các tác vụ quen thuộc: mở nhiều tab, làm slide, xử lý bảng tính, gọi video và chỉnh ảnh cơ bản vẫn mượt mà.
4. Nhấn vào thời lượng pin dài, máy chạy êm, không ồn, phù hợp dùng ở lớp học, văn phòng, quán cà phê hoặc khi di chuyển.
5. Kết video bằng thông điệp: MacBook Air M3 13 inch là lựa chọn cân bằng cho người muốn một chiếc MacBook nhỏ gọn, hiệu năng tốt và dùng ổn định lâu dài.

Caption đề xuất:
MacBook Air M3 13 inch - mỏng nhẹ, pin lâu, hiệu năng M3 mượt mà cho học tập, văn phòng và sáng tạo nội dung cơ bản mỗi ngày.
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
                    cta_label = 'Xem MacBook Air M3',
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
                    'DRAFT', NULL, $4, $5, 'Xem MacBook Air M3', $6,
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
