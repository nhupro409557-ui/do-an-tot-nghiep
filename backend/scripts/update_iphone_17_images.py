import asyncio
import json

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
BASE_URL = "/images/products/iphone-17"

BLACK_COVER = f"{BASE_URL}/black/cover.webp"
BLACK_IMAGES = [
    f"{BASE_URL}/black/gallery-01.webp",
    f"{BASE_URL}/black/gallery-02.webp",
]

WHITE_COVER = f"{BASE_URL}/white/cover.webp"
WHITE_IMAGES: list[str] = []

MIST_BLUE_COVER = f"{BASE_URL}/mist-blue/cover.webp"
MIST_BLUE_IMAGES = [
    f"{BASE_URL}/mist-blue/gallery-01.webp",
]

COMMON_IMAGES = [
    f"{BASE_URL}/common/gallery-01.webp",
    f"{BASE_URL}/common/gallery-02.webp",
    f"{BASE_URL}/common/gallery-03.webp",
    f"{BASE_URL}/common/gallery-04.webp",
    f"{BASE_URL}/common/gallery-05.jpg",
    f"{BASE_URL}/common/gallery-06.webp",
    f"{BASE_URL}/common/gallery-07.webp",
    f"{BASE_URL}/common/gallery-08.webp",
    f"{BASE_URL}/common/gallery-09.webp",
]


async def update_color_variants(conn: asyncpg.Connection, product_id, color_like: str, cover: str, images: list[str]) -> str:
    return await conn.execute(
        """
        UPDATE product_variants
        SET image_url = $1,
            images = $2::jsonb,
            updated_at = NOW()
        WHERE product_id = $3
          AND deleted_at IS NULL
          AND LOWER(color_name) LIKE $4
        """,
        cover,
        json.dumps(images),
        product_id,
        f"%{color_like}%",
    )


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        products = await conn.fetch(
            """
            SELECT id, sku, name
            FROM products
            WHERE deleted_at IS NULL
              AND name = 'iPhone 17'
              AND sku IN ('IP17', 'IP17-BK-256GB')
            ORDER BY CASE WHEN sku = 'IP17' THEN 0 ELSE 1 END
            """
        )
        if not products:
            print("No iPhone 17 products found.")
            return

        for product in products:
            await conn.execute(
                """
                UPDATE products
                SET image_url = $1,
                    images = $2::jsonb,
                    updated_at = NOW()
                WHERE id = $3
                """,
                BLACK_COVER,
                json.dumps(COMMON_IMAGES),
                product["id"],
            )
            updated_black = await update_color_variants(conn, product["id"], "đen", BLACK_COVER, BLACK_IMAGES)
            updated_white = await update_color_variants(conn, product["id"], "trắng", WHITE_COVER, WHITE_IMAGES)
            updated_blue = await update_color_variants(conn, product["id"], "xanh sương mù", MIST_BLUE_COVER, MIST_BLUE_IMAGES)
            print(
                f"Updated {product['sku']} {product['name']}: "
                f"black={updated_black}, white={updated_white}, mist_blue={updated_blue}"
            )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
