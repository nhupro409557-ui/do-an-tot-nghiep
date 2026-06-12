import asyncio
from uuid import uuid4

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
PRODUCT_SKU = "S26U"
VIDEO_TITLE = "Samsung Galaxy S26 Ultra - Galaxy AI, S Pen, camera 200MP đỉnh cao"

DESCRIPTION = (
    "Nội dung nháp cho video giới thiệu Samsung Galaxy S26 Ultra: tập trung vào Galaxy AI, "
    "S Pen tích hợp, màn hình Dynamic AMOLED 2X, camera 200MP, Space Zoom và hiệu năng Snapdragon for Galaxy."
)

CONTENT_BODY = """Samsung Galaxy S26 Ultra phù hợp với người dùng cần một flagship Android toàn diện cho công việc, sáng tạo nội dung, chụp ảnh, quay video và giải trí cao cấp.

Gợi ý kịch bản video:
1. Mở đầu bằng cảnh cận thiết kế khung Titanium, mặt kính Gorilla Armor 2 và các màu Đen Classic, Tím Cobalt, Trắng Classic, Xanh Sky Blue để nhấn mạnh vẻ cao cấp.
2. Chuyển sang màn hình Dynamic AMOLED 2X 6.9 inch, độ phân giải QHD+, tần số quét thích ứng 1-120Hz và độ sáng cao khi xem phim, chơi game hoặc dùng ngoài trời.
3. Giới thiệu Galaxy AI trong các tình huống thực tế: tóm tắt nội dung, hỗ trợ chỉnh ảnh, dịch nhanh, tìm kiếm thông minh và tối ưu công việc hằng ngày.
4. Nhấn vào S Pen tích hợp cho ghi chú nhanh, ký tài liệu, phác thảo ý tưởng và điều khiển máy chính xác hơn.
5. Trình bày hệ thống camera 200MP, góc siêu rộng 50MP, tele 3x, tiềm vọng 5x và Space Zoom 100x qua các cảnh chân dung, phong cảnh, zoom xa và chụp đêm.
6. Nêu trải nghiệm hiệu năng: Snapdragon 8 Elite Gen 5 for Galaxy, Wi-Fi 7, Samsung DeX, Knox Security, pin 5000 mAh và sạc nhanh 60W cho nhu cầu dùng cả ngày.
7. Kết video bằng thông điệp: Galaxy S26 Ultra là lựa chọn cho người muốn một chiếc máy Android cao cấp, nhiều công cụ AI, bút S Pen và camera mạnh trong cùng một thiết bị.

Caption đề xuất:
Samsung Galaxy S26 Ultra - Galaxy AI thông minh, S Pen tiện dụng, camera 200MP và màn hình Dynamic AMOLED 2X cho trải nghiệm flagship toàn diện.
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
                    cta_label = 'Xem Galaxy S26 Ultra',
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
                    'DRAFT', NULL, $4, $5, 'Xem Galaxy S26 Ultra', $6,
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
