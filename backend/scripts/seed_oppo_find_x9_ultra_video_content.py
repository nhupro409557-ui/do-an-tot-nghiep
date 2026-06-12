import asyncio
from uuid import uuid4

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
PRODUCT_SKU = "OP-FX9U"
VIDEO_TITLE = "OPPO Find X9 Ultra - Camera Hasselblad, pin lớn, hiệu năng flagship"

DESCRIPTION = (
    "Nội dung nháp cho video giới thiệu OPPO Find X9 Ultra: tập trung vào hệ thống camera Hasselblad, "
    "màn hình LTPO AMOLED 144Hz, pin 7050 mAh, sạc nhanh 100W và hiệu năng cao cấp."
)

CONTENT_BODY = """OPPO Find X9 Ultra hướng đến người dùng muốn một chiếc smartphone flagship mạnh mẽ, màn hình đẹp, pin lớn và camera linh hoạt cho chụp ảnh, quay video hằng ngày.

Gợi ý kịch bản video:
1. Mở đầu bằng cảnh cận máy với mặt lưng da sinh thái, cụm camera lớn và hai màu Nâu Lãnh Nguyên, Cam Hẻm Núi để nhấn mạnh vẻ cao cấp.
2. Chuyển sang màn hình LTPO AMOLED 6.82 inch QHD+, tần số quét 144Hz và độ sáng cao khi xem ảnh, video, chơi game hoặc dùng ngoài trời.
3. Giới thiệu hệ thống camera Hasselblad với camera chính 200MP, tele 200MP, tele 10x và camera siêu rộng 50MP; minh họa các cảnh chụp chân dung, zoom xa, phong cảnh và thiếu sáng.
4. Nhấn vào khả năng quay video 8K, 4K tốc độ cao, chống rung OIS/EIS và Dolby Vision cho người thích quay nội dung bằng điện thoại.
5. Nêu điểm dùng hằng ngày: chip Snapdragon 8 Elite Gen 5, pin 7050 mAh, sạc nhanh 100W, sạc không dây 50W, Wi-Fi 7, kháng nước bụi IP68/IP69.
6. Kết video bằng thông điệp: OPPO Find X9 Ultra phù hợp với người cần một flagship Android nổi bật về camera, màn hình, pin và trải nghiệm cao cấp.

Caption đề xuất:
OPPO Find X9 Ultra - camera Hasselblad đa tiêu cự, màn hình 144Hz sắc nét, pin 7050 mAh và sạc nhanh 100W cho trải nghiệm flagship toàn diện.
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
                    cta_label = 'Xem OPPO Find X9 Ultra',
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
                    'DRAFT', NULL, $4, $5, 'Xem OPPO Find X9 Ultra', $6,
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
