import asyncio
import json

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"

HONOR_400_BASE_URL = "/images/products/honor-400-5g"
HONOR_400_PRO_BASE_URL = "/images/products/honor-400-pro"

HONOR_400_GOLD_COVER = f"{HONOR_400_BASE_URL}/gold/cover.jpg"
HONOR_400_GOLD_IMAGES = [
    f"{HONOR_400_BASE_URL}/gold/gallery-01.jpg",
    f"{HONOR_400_BASE_URL}/gold/gallery-02.webp",
    f"{HONOR_400_BASE_URL}/gold/gallery-03.webp",
    f"{HONOR_400_BASE_URL}/gold/gallery-04.webp",
    f"{HONOR_400_BASE_URL}/gold/gallery-05.webp",
]
HONOR_400_COMMON_IMAGES = [
    f"{HONOR_400_BASE_URL}/common/gallery-01.webp",
    f"{HONOR_400_BASE_URL}/common/gallery-02.webp",
    f"{HONOR_400_BASE_URL}/common/gallery-03.webp",
    f"{HONOR_400_BASE_URL}/common/gallery-04.webp",
    f"{HONOR_400_BASE_URL}/common/gallery-05.webp",
]

HONOR_400_PRO_BLACK_COVER = f"{HONOR_400_PRO_BASE_URL}/black/cover.jpg"
HONOR_400_PRO_BLACK_IMAGES = [
    f"{HONOR_400_PRO_BASE_URL}/black/gallery-01.webp",
    f"{HONOR_400_PRO_BASE_URL}/black/gallery-02.webp",
    f"{HONOR_400_PRO_BASE_URL}/black/gallery-03.webp",
    f"{HONOR_400_PRO_BASE_URL}/black/gallery-04.webp",
    f"{HONOR_400_PRO_BASE_URL}/black/gallery-05.jpg",
]
HONOR_400_PRO_GRAY_COVER = f"{HONOR_400_PRO_BASE_URL}/gray/cover.jpg"
HONOR_400_PRO_GRAY_IMAGES = [
    f"{HONOR_400_PRO_BASE_URL}/gray/gallery-01.webp",
    f"{HONOR_400_PRO_BASE_URL}/gray/gallery-02.webp",
    f"{HONOR_400_PRO_BASE_URL}/gray/gallery-03.jpg",
]


async def update_honor_400(conn: asyncpg.Connection) -> None:
    product = await conn.fetchrow("SELECT id, name FROM products WHERE sku = 'HN-400'")
    if not product:
        print("Product HN-400 not found.")
        return

    await conn.execute(
        """
        UPDATE products
        SET image_url = $1,
            images = $2::jsonb,
            updated_at = NOW()
        WHERE id = $3
        """,
        HONOR_400_GOLD_COVER,
        json.dumps(HONOR_400_COMMON_IMAGES),
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
        HONOR_400_GOLD_COVER,
        json.dumps(HONOR_400_GOLD_IMAGES),
        product["id"],
    )
    print(f"Updated images for {product['name']}: {updated_gold}")


async def update_honor_400_pro(conn: asyncpg.Connection) -> None:
    product = await conn.fetchrow("SELECT id, name FROM products WHERE sku = 'HN-400P'")
    if not product:
        print("Product HN-400P not found.")
        return

    await conn.execute(
        """
        UPDATE products
        SET image_url = $1,
            images = '[]'::jsonb,
            updated_at = NOW()
        WHERE id = $2
        """,
        HONOR_400_PRO_BLACK_COVER,
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
        HONOR_400_PRO_BLACK_COVER,
        json.dumps(HONOR_400_PRO_BLACK_IMAGES),
        product["id"],
    )
    updated_gray = await conn.execute(
        """
        UPDATE product_variants
        SET image_url = $1,
            images = $2::jsonb,
            updated_at = NOW()
        WHERE product_id = $3
          AND deleted_at IS NULL
          AND LOWER(color_name) LIKE '%xám%'
        """,
        HONOR_400_PRO_GRAY_COVER,
        json.dumps(HONOR_400_PRO_GRAY_IMAGES),
        product["id"],
    )
    print(f"Updated images for {product['name']}: {updated_black}, {updated_gray}")


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await update_honor_400(conn)
        await update_honor_400_pro(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
