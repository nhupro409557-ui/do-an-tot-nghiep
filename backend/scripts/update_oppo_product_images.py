import asyncio
import json
from pathlib import Path

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"

PUBLIC_PRODUCTS_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "images" / "products"


def image_set(product_slug: str, color_slug: str) -> tuple[str, list[str]]:
    folder = PUBLIC_PRODUCTS_DIR / product_slug / color_slug
    covers = sorted(folder.glob("cover.*"))
    if not covers:
        raise FileNotFoundError(f"Không tìm thấy ảnh đại diện trong {folder}")

    base_url = f"/images/products/{product_slug}/{color_slug}"
    cover = f"{base_url}/{covers[0].name}"
    gallery = [
        f"{base_url}/{file.name}"
        for file in sorted(folder.glob("gallery-*"))
    ]
    return cover, gallery


def gallery_set(product_slug: str, folder_slug: str) -> list[str]:
    folder = PUBLIC_PRODUCTS_DIR / product_slug / folder_slug
    if not folder.exists():
        return []
    base_url = f"/images/products/{product_slug}/{folder_slug}"
    return [
        f"{base_url}/{file.name}"
        for file in sorted(folder.glob("gallery-*"))
    ]


PRODUCTS = [
    {
        "name": "OPPO Reno15 5G",
        "product_slug": "oppo-reno-15-5g",
        "default_color": "white",
        "common": "common",
        "variants": [
            ("Trắng Cực Quang", "white"),
            ("Xanh Chạng Vạng", "blue"),
        ],
    },
    {
        "name": "OPPO Reno15 F 5G",
        "product_slug": "oppo-reno-15-f-5g",
        "default_color": "pink",
        "variants": [
            ("Hồng Rực Rỡ", "pink"),
            ("Xanh Dương", "blue"),
            ("Xanh Nhạt", "light-blue"),
        ],
    },
    {
        "name": "OPPO Find N6",
        "product_slug": "oppo-find-n6",
        "default_color": "orange",
        "common": "common",
        "variants": [
            ("Cam Nở Rộ", "orange"),
            ("Titan Ánh Sao", "titan"),
        ],
    },
    {
        "name": "OPPO Find X9 Ultra",
        "product_slug": "oppo-find-x9-ultra",
        "default_color": "brown",
        "variants": [
            ("Cam Hẻm Núi", "orange"),
            ("Nâu Lãnh Nguyên", "brown"),
        ],
    },
    {
        "name": "OPPO Find X9s",
        "product_slug": "oppo-find-x9s",
        "default_color": "sky-gray",
        "variants": [
            ("Cam Hoàng Hôn", "sunset-orange"),
            ("Tím Lavender", "lavender"),
            ("Xám Bầu Trời", "sky-gray"),
        ],
    },
    {
        "name": "OPPO Find X8",
        "product_slug": "oppo-find-x8",
        "default_color": "black",
        "common": "common",
        "variants": [
            ("Đen Không Gian", "black"),
            ("Xám Sao Băng", "gray"),
        ],
    },
]


async def update_product(conn: asyncpg.Connection, spec: dict) -> None:
    product = await conn.fetchrow(
        """
        SELECT id, name
        FROM products
        WHERE name = $1
          AND deleted_at IS NULL
        ORDER BY created_at NULLS LAST
        LIMIT 1
        """,
        spec["name"],
    )
    if not product:
        print(f"Không tìm thấy sản phẩm {spec['name']}.")
        return

    default_cover, default_gallery = image_set(spec["product_slug"], spec["default_color"])
    product_images = gallery_set(spec["product_slug"], spec.get("common", "")) or default_gallery

    await conn.execute(
        """
        UPDATE products
        SET image_url = $1,
            images = $2::jsonb,
            updated_at = NOW()
        WHERE id = $3
        """,
        default_cover,
        json.dumps(product_images, ensure_ascii=False),
        product["id"],
    )

    print(f"Đã cập nhật ảnh sản phẩm {product['name']}.")

    for color_name, color_slug in spec["variants"]:
        cover, gallery = image_set(spec["product_slug"], color_slug)
        result = await conn.execute(
            """
            UPDATE product_variants
            SET image_url = $1,
                images = $2::jsonb,
                updated_at = NOW()
            WHERE product_id = $3
              AND deleted_at IS NULL
              AND is_active IS TRUE
              AND color_name = $4
            """,
            cover,
            json.dumps(gallery, ensure_ascii=False),
            product["id"],
            color_name,
        )
        print(f"  {color_name}: {result}")


async def update_find_n3(conn: asyncpg.Connection) -> None:
    product = await conn.fetchrow(
        """
        SELECT id, name
        FROM products
        WHERE name = 'OPPO Find N3'
          AND deleted_at IS NULL
        ORDER BY created_at NULLS LAST
        LIMIT 1
        """
    )
    if not product:
        print("Không tìm thấy sản phẩm OPPO Find N3.")
        return

    black_cover, black_gallery = image_set("oppo-find-n3", "black")
    gold_cover, gold_gallery = image_set("oppo-find-n3", "gold")
    images = black_gallery + [gold_cover] + gold_gallery
    await conn.execute(
        """
        UPDATE products
        SET image_url = $1,
            images = $2::jsonb,
            updated_at = NOW()
        WHERE id = $3
        """,
        black_cover,
        json.dumps(images, ensure_ascii=False),
        product["id"],
    )
    print(f"Đã cập nhật ảnh sản phẩm {product['name']}.")


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        for spec in PRODUCTS:
            await update_product(conn, spec)
        await update_find_n3(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
