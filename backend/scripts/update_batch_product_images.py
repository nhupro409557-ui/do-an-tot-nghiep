import asyncio
import json
import shutil
import unicodedata
from pathlib import Path

import asyncpg


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_PRODUCTS_DIR = PROJECT_ROOT / "frontend" / "public" / "images" / "products"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def normalized_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")


def is_cover_file(path: Path) -> bool:
    name = path.stem.lower()
    return "dai dien" in normalized_text(name) or "dia dien" in normalized_text(name)


def image_files(folder: Path) -> list[Path]:
    return sorted(
        [item for item in folder.iterdir() if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda item: normalized_text(item.name),
    )


def build_image_set(source: Path, product_slug: str, folder_slug: str) -> tuple[str, list[str]]:
    files = image_files(source)
    if not files:
        raise FileNotFoundError(f"Không tìm thấy ảnh trong {source}")

    cover_source = next((file for file in files if is_cover_file(file)), files[0])
    gallery_sources = [file for file in files if file != cover_source]

    target = PUBLIC_PRODUCTS_DIR / product_slug / folder_slug
    target.mkdir(parents=True, exist_ok=True)

    cover_name = f"cover{cover_source.suffix.lower()}"
    shutil.copy2(cover_source, target / cover_name)

    gallery_urls: list[str] = []
    for index, source_file in enumerate(gallery_sources, start=1):
        gallery_name = f"gallery-{index:02d}{source_file.suffix.lower()}"
        shutil.copy2(source_file, target / gallery_name)
        gallery_urls.append(f"/images/products/{product_slug}/{folder_slug}/{gallery_name}")

    cover_url = f"/images/products/{product_slug}/{folder_slug}/{cover_name}"
    return cover_url, gallery_urls


PRODUCT_SPECS = [
    {
        "name": "AirPods Pro 2 USB-C",
        "source": "apple aripods pro 2 usb",
        "product_slug": "airpods-pro-2-usbc",
        "default_folder": "common",
        "sets": [{"source": "", "folder": "common", "colors": None}],
    },
    {
        "name": "Apple Watch Ultra 2",
        "source": "Apple Watch Ultra 2",
        "product_slug": "apple-watch-ultra-2",
        "default_folder": "black",
        "sets": [{"source": "Đen", "folder": "black", "colors": ["Titan Đen"]}],
    },
    {
        "name": "iPad A16 Wifi",
        "source": "iPad A16 Wifi",
        "product_slug": "ipad-a16-wifi",
        "default_folder": "common",
        "sets": [{"source": "", "folder": "common", "colors": None}],
    },
    {
        "name": "iPad Pro M4 11 inch",
        "source": "iPad Pro M4 11 inch",
        "product_slug": "ipad-pro-m4",
        "default_folder": "common",
        "sets": [{"source": "dùng chung", "folder": "common", "colors": None}],
    },
    {
        "name": "MacBook Air M3 13 inch",
        "source": "MacBook Air M3 13 inch",
        "product_slug": "macbook-air-m3",
        "default_folder": "common",
        "sets": [{"source": "", "folder": "common", "colors": None}],
    },
    {
        "name": "MacBook Neo 13 inch A18 Pro 2026",
        "source": "MacBook Neo 13 inch A18 Pro 2026",
        "product_slug": "macbook-neo-13-a18-pro-2026",
        "default_folder": "common",
        "sets": [{"source": "", "folder": "common", "colors": None}],
    },
    {
        "name": "Samsung Galaxy A17 5G",
        "source": "Samsung Galaxy A17 5G",
        "product_slug": "samsung-galaxy-a17-5g",
        "default_folder": "black",
        "sets": [
            {"source": "đen", "folder": "black", "colors": ["Đen"]},
            {"source": "Xám", "folder": "gray", "colors": ["Xám"]},
            {"source": "xanh", "folder": "blue", "colors": ["Xanh Lam"]},
        ],
    },
    {
        "name": "Samsung Galaxy A57 5G",
        "source": "Samsung Galaxy A57 5G",
        "product_slug": "samsung-galaxy-a57-5g",
        "default_folder": "navy",
        "sets": [
            {"source": "Xanh dương", "folder": "navy", "colors": ["Xanh Navy"]},
            {"source": "Xám", "folder": "gray", "colors": ["Xám"]},
            {"source": "Tím", "folder": "lilac", "colors": ["Tím Lilac"]},
            {"source": "Đen", "folder": "black", "colors": []},
        ],
    },
    {
        "name": "Samsung Galaxy S26",
        "source": "Samsung Galaxy S26",
        "product_slug": "samsung-galaxy-s26",
        "default_folder": "black",
        "sets": [
            {"source": "Đen", "folder": "black", "colors": ["Đen Classic"]},
            {"source": "Trắng", "folder": "white", "colors": ["Trắng Classic"]},
            {"source": "Tím", "folder": "cobalt-violet", "colors": ["Tím Cobalt"]},
            {"source": "xanh", "folder": "sky-blue", "colors": ["Xanh Sky Blue"]},
        ],
    },
    {
        "name": "Samsung Galaxy S26 Ultra",
        "source": "Samsung Galaxy S26 Ultra",
        "product_slug": "samsung-galaxy-s26-ultra",
        "default_folder": "black",
        "sets": [
            {"source": "Đen", "folder": "black", "colors": ["Đen Classic"]},
            {"source": "Trắng", "folder": "white", "colors": ["Trắng Classic"]},
            {"source": "Tím", "folder": "cobalt-violet", "colors": ["Tím Cobalt"]},
            {"source": "Xanh", "folder": "sky-blue", "colors": ["Xanh Sky Blue"]},
        ],
    },
]


async def update_product(conn: asyncpg.Connection, spec: dict) -> None:
    source_root = PROJECT_ROOT / spec["source"]
    sets: dict[str, tuple[str, list[str], list[str] | None]] = {}

    for item in spec["sets"]:
        source = source_root / item["source"] if item["source"] else source_root
        cover, gallery = build_image_set(source, spec["product_slug"], item["folder"])
        sets[item["folder"]] = (cover, gallery, item["colors"])

    default_cover, default_gallery, _ = sets[spec["default_folder"]]
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

    product_images: list[str] = []
    for _folder, (_cover, gallery, _colors) in sets.items():
        product_images.extend(gallery)
    if not product_images:
        product_images = default_gallery

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

    for _folder, (cover, gallery, colors) in sets.items():
        if colors == []:
            continue
        if colors is None:
            result = await conn.execute(
                """
                UPDATE product_variants
                SET image_url = $1,
                    images = $2::jsonb,
                    updated_at = NOW()
                WHERE product_id = $3
                  AND deleted_at IS NULL
                  AND is_active IS TRUE
                """,
                cover,
                json.dumps(gallery, ensure_ascii=False),
                product["id"],
            )
            print(f"  Tất cả biến thể: {result}")
            continue

        for color in colors:
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
                color,
            )
            print(f"  {color}: {result}")


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        for spec in PRODUCT_SPECS:
            await update_product(conn, spec)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
