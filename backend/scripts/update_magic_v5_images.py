import asyncio
import json

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"

BASE_URL = "/images/products/honor-magic-v5"

WHITE_COVER = f"{BASE_URL}/white/cover.jpg"
GOLD_COVER = f"{BASE_URL}/gold/cover.jpg"

WHITE_IMAGES = [
    f"{BASE_URL}/white/gallery-01.webp",
    f"{BASE_URL}/white/gallery-02.jpg",
    f"{BASE_URL}/white/gallery-03.webp",
    f"{BASE_URL}/white/gallery-04.jpg",
    f"{BASE_URL}/white/gallery-05.jpg",
    f"{BASE_URL}/white/gallery-06.jpg",
    f"{BASE_URL}/white/gallery-07.jpg",
    f"{BASE_URL}/white/gallery-08.webp",
    f"{BASE_URL}/white/gallery-09.jpg",
    f"{BASE_URL}/white/gallery-10.jpg",
    f"{BASE_URL}/white/gallery-11.jpg",
]

GOLD_IMAGES = [
    f"{BASE_URL}/gold/gallery-01.webp",
    f"{BASE_URL}/gold/gallery-02.jpg",
    f"{BASE_URL}/gold/gallery-03.jpg",
    f"{BASE_URL}/gold/gallery-04.webp",
    f"{BASE_URL}/gold/gallery-05.jpg",
    f"{BASE_URL}/gold/gallery-06.webp",
    f"{BASE_URL}/gold/gallery-07.webp",
    f"{BASE_URL}/gold/gallery-08.webp",
    f"{BASE_URL}/gold/gallery-09.webp",
    f"{BASE_URL}/gold/gallery-10.jpg",
    f"{BASE_URL}/gold/gallery-11.jpg",
    f"{BASE_URL}/gold/gallery-12.webp",
    f"{BASE_URL}/gold/gallery-13.jpg",
]

COMMON_IMAGES = [
    f"{BASE_URL}/common/gallery-01.webp",
    f"{BASE_URL}/common/gallery-02.jpg",
    f"{BASE_URL}/common/gallery-03.webp",
    f"{BASE_URL}/common/gallery-04.jpg",
    f"{BASE_URL}/common/gallery-05.webp",
]


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    product = await conn.fetchrow("SELECT id, name FROM products WHERE sku = 'HN-MGV5'")
    if not product:
        print("Product HN-MGV5 not found.")
        await conn.close()
        return

    product_images = COMMON_IMAGES
    await conn.execute(
        """
        UPDATE products
        SET image_url = $1,
            images = $2::jsonb,
            updated_at = NOW()
        WHERE id = $3
        """,
        WHITE_COVER,
        json.dumps(product_images),
        product["id"],
    )

    updated_white = await conn.execute(
        """
        UPDATE product_variants
        SET image_url = $1,
            images = $2::jsonb,
            updated_at = NOW()
        WHERE product_id = $3
          AND deleted_at IS NULL
          AND LOWER(color_name) LIKE '%trắng%'
        """,
        WHITE_COVER,
        json.dumps(WHITE_IMAGES),
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

    print(f"Updated product images for {product['name']}.")
    print(updated_white)
    print(updated_gold)
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
