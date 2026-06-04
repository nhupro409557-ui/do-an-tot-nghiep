import asyncio
import json

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
BASE_URL = "/images/products/iphone-17-pro"

SILVER_COVER = f"{BASE_URL}/silver/cover.webp"
SILVER_IMAGES = [f"{BASE_URL}/silver/gallery-{index:02d}.webp" for index in range(1, 8)]

ORANGE_COVER = f"{BASE_URL}/cosmic-orange/cover.webp"
ORANGE_IMAGES = [f"{BASE_URL}/cosmic-orange/gallery-{index:02d}.webp" for index in range(1, 8)]

BLUE_COVER = f"{BASE_URL}/deep-blue/cover.webp"
BLUE_IMAGES = [f"{BASE_URL}/deep-blue/gallery-{index:02d}.webp" for index in range(1, 5)]

COMMON_IMAGES = [f"{BASE_URL}/common/gallery-{index:02d}.webp" for index in range(1, 8)]


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
            SELECT id, sku, name, status
            FROM products
            WHERE deleted_at IS NULL
              AND name = 'iPhone 17 Pro'
            ORDER BY CASE WHEN sku = 'IP17P' THEN 0 ELSE 1 END, sku
            """
        )
        if not products:
            print("No iPhone 17 Pro products found.")
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
                ORANGE_COVER,
                json.dumps(COMMON_IMAGES),
                product["id"],
            )
            updated_silver = await update_color_variants(conn, product["id"], "bạc", SILVER_COVER, SILVER_IMAGES)
            updated_orange = await update_color_variants(conn, product["id"], "cam vũ trụ", ORANGE_COVER, ORANGE_IMAGES)
            updated_blue = await update_color_variants(conn, product["id"], "xanh sâu", BLUE_COVER, BLUE_IMAGES)
            print(
                f"Updated {product['sku']} {product['name']} ({product['status']}): "
                f"silver={updated_silver}, orange={updated_orange}, blue={updated_blue}"
            )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
