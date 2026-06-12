import asyncio
from uuid import uuid4

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
PRODUCT_SKU = "IPADA16"
VIDEO_TITLE = "iPad A16 Wifi - Màn hình lớn, học tập linh hoạt, giải trí mượt mà"

DESCRIPTION = (
    "Nội dung nháp cho video giới thiệu iPad A16 Wifi: tập trung vào màn hình Liquid Retina 10.9 inch, "
    "chip A16 Bionic, Apple Pencil USB-C, Touch ID, camera 12MP và nhu cầu học tập, làm việc, giải trí."
)

CONTENT_BODY = """iPad A16 Wifi phù hợp với người dùng cần một chiếc máy tính bảng dễ dùng, màn hình rộng, hiệu năng ổn định cho học tập, ghi chú, làm việc nhẹ và giải trí hằng ngày.

Gợi ý kịch bản video:
1. Mở đầu bằng cảnh cầm iPad trên tay, đặt trong balo hoặc dùng trên bàn học để nhấn mạnh thiết kế mỏng nhẹ, dễ mang theo.
2. Chuyển sang màn hình Liquid Retina 10.9 inch khi đọc tài liệu, xem bài giảng, duyệt web, xem phim và chỉnh ảnh nhẹ để thể hiện không gian hiển thị thoải mái.
3. Giới thiệu chip Apple A16 Bionic qua các tác vụ quen thuộc: mở nhiều ứng dụng, học online, làm bài thuyết trình, ghi chú và chơi game giải trí.
4. Nhấn vào Apple Pencil USB-C cho ghi chú, vẽ phác thảo, đánh dấu tài liệu; Touch ID ở nút nguồn giúp mở khóa nhanh và tiện.
5. Trình bày camera trước 12MP góc siêu rộng cho gọi video, camera sau 12MP quay 4K và loa stereo cho học tập, họp online, xem phim.
6. Nêu các lựa chọn màu Bạc, Vàng, Hồng, Xanh cùng các phiên bản A16 Wifi 128GB, 256GB, 512GB và bản 5G cho người cần kết nối linh hoạt hơn.
7. Kết video bằng thông điệp: iPad A16 Wifi là lựa chọn cân bằng cho học sinh, sinh viên, gia đình và người dùng cần một thiết bị Apple gọn nhẹ, dễ dùng mỗi ngày.

Caption đề xuất:
iPad A16 Wifi - màn hình Liquid Retina 10.9 inch, chip A16 Bionic, hỗ trợ Apple Pencil USB-C và nhiều màu trẻ trung cho học tập, làm việc, giải trí.
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
                    cta_label = 'Xem iPad A16 Wifi',
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
                    'DRAFT', NULL, $4, $5, 'Xem iPad A16 Wifi', $6,
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
