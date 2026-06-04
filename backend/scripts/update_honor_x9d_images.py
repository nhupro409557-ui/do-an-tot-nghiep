import asyncio
import json

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
BASE_URL = "/images/products/honor-x9d"

BLACK_COVER = f"{BASE_URL}/black/cover.webp"
BLACK_IMAGES = [
    f"{BASE_URL}/black/gallery-01.jpg",
    f"{BASE_URL}/black/gallery-02.jpg",
    f"{BASE_URL}/black/gallery-03.jpg",
    f"{BASE_URL}/black/gallery-04.jpg",
    f"{BASE_URL}/black/gallery-05.webp",
    f"{BASE_URL}/black/gallery-06.webp",
    f"{BASE_URL}/black/gallery-07.jpg",
    f"{BASE_URL}/black/gallery-08.webp",
]

GOLD_COVER = f"{BASE_URL}/gold/cover.jpg"
GOLD_IMAGES = [
    f"{BASE_URL}/gold/gallery-01.jpg",
    f"{BASE_URL}/gold/gallery-02.webp",
    f"{BASE_URL}/gold/gallery-03.webp",
    f"{BASE_URL}/gold/gallery-04.jpg",
    f"{BASE_URL}/gold/gallery-05.webp",
    f"{BASE_URL}/gold/gallery-06.jpg",
    f"{BASE_URL}/gold/gallery-07.webp",
    f"{BASE_URL}/gold/gallery-08.webp",
    f"{BASE_URL}/gold/gallery-09.jpg",
    f"{BASE_URL}/gold/gallery-10.jpg",
    f"{BASE_URL}/gold/gallery-11.jpg",
]

COMMON_IMAGES = [
    f"{BASE_URL}/common/gallery-01.jpg",
    f"{BASE_URL}/common/gallery-02.jpg",
    f"{BASE_URL}/common/gallery-03.jpg",
    f"{BASE_URL}/common/gallery-04.webp",
    f"{BASE_URL}/common/gallery-05.jpg",
]


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        product = await conn.fetchrow("SELECT id, name FROM products WHERE sku = 'HN-X9D'")
        if not product:
            print("Product HN-X9D not found.")
            return

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
        updated_black = await conn.execute(
            """
            UPDATE product_variants
            SET image_url = $1,
                images = $2::jsonb,
                updated_at = NOW()
            WHERE product_id = $3
              AND deleted_at IS NULL
              AND LOWER(color_name) LIKE '%đen%'
            """,
            BLACK_COVER,
            json.dumps(BLACK_IMAGES),
            product["id"],
        )
        updated_gold = await conn.execute(
            """
            UPDATE product_variants
            SET image_url = $1,
                images = $2::jsonb,
                updated_at = NOW()
            WHERE product_id = $3
              AND deleted_at IS NULL
              AND LOWER(color_name) LIKE '%vàng%'
            """,
            GOLD_COVER,
            json.dumps(GOLD_IMAGES),
            product["id"],
        )
        print(f"Updated images for {product['name']}: {updated_black}, {updated_gold}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
