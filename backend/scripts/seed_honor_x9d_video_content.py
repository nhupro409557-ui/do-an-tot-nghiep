import asyncio
from uuid import uuid4

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
PRODUCT_SKU = "HN-X9D"
VIDEO_TITLE = "HONOR X9d 5G - Pin trâu, màn hình sáng, bền bỉ mỗi ngày"

DESCRIPTION = (
    "Nội dung nháp cho video giới thiệu HONOR X9d 5G: tập trung vào pin lớn, "
    "màn hình AMOLED sáng rõ, thiết kế bền bỉ và trải nghiệm sử dụng hằng ngày."
)

CONTENT_BODY = """HONOR X9d 5G được xây dựng cho người dùng cần một chiếc điện thoại bền bỉ, pin lâu và màn hình đẹp trong tầm giá.

Gợi ý kịch bản video:
1. Mở đầu bằng cảnh cầm máy trên tay, nhấn mạnh thiết kế mỏng, chắc chắn và màu sắc sang.
2. Chuyển sang màn hình AMOLED lớn, độ sáng cao, phù hợp xem phim, lướt web và dùng ngoài trời.
3. Nhấn vào viên pin dung lượng lớn, thời lượng dùng dài trong ngày, phù hợp người đi học, đi làm hoặc di chuyển nhiều.
4. Giới thiệu camera 108MP cho ảnh chi tiết, màu sắc rõ, đủ dùng cho nhu cầu chụp đời thường và đăng mạng xã hội.
5. Kết bằng thông điệp: HONOR X9d 5G là lựa chọn gọn gàng cho người muốn máy đẹp, pin khỏe, màn hình tốt và độ bền cao.

Caption đề xuất:
HONOR X9d 5G - pin khỏe, màn hình đẹp, cầm chắc tay. Một lựa chọn đáng cân nhắc nếu bạn cần chiếc điện thoại bền bỉ để dùng lâu dài mỗi ngày.
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
                    cta_label = 'Xem HONOR X9d 5G',
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
                    'DRAFT', NULL, $4, $5, 'Xem HONOR X9d 5G', $6,
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

        category_ids = [product["subcategory_id"], product["category_id"]]
        for category_id in [item for item in category_ids if item]:
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
