import asyncio
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
import httpx
from ddgs import DDGS


DATABASE_URL = "postgresql://postgres:anhnhu057@localhost:5432/postgres"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_PRODUCTS_DIR = PROJECT_ROOT / "frontend" / "public" / "images" / "products"

MAX_IMAGES_PER_PRODUCT = 4
MIN_IMAGE_BYTES = 8_000
SEARCH_TIMEOUT_SECONDS = 20

IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

PREFERRED_SOURCES = (
    "apple.com",
    "samsung.com",
    "mi.com",
    "mi.com.vn",
    "sony.com",
    "razer.com",
    "anker.com",
    "ugreen.com",
    "belkin.com",
    "jbl.com",
    "marshallheadphones.com",
    "garmin.com",
    "gopro.com",
    "dji.com",
    "ezviz.com",
    "mophie.com",
    "realme.com",
    "vivo.com",
)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug or "product"


def images_need_fix(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped == "[]":
            return True
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return True
        return not isinstance(parsed, list) or len(parsed) == 0
    return not isinstance(value, list) or len(value) == 0


def local_file_missing(url: str | None) -> bool:
    if not url or not url.startswith("/images/"):
        return False
    return not (PROJECT_ROOT / "frontend" / "public" / url.lstrip("/")).exists()


def image_values(value) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, str)]
    return []


def source_score(result: dict) -> tuple[int, int]:
    source = (result.get("source") or urlparse(result.get("url") or "").netloc).lower()
    preferred = 0 if any(domain in source for domain in PREFERRED_SOURCES) else 1
    try:
        area = int(result.get("width") or 0) * int(result.get("height") or 0)
    except (TypeError, ValueError):
        area = 0
    return preferred, -area


def search_images(product_name: str, brand: str | None) -> list[dict]:
    query = f"{brand or ''} {product_name} official product images".strip()
    with DDGS(timeout=SEARCH_TIMEOUT_SECONDS) as ddgs:
        results = list(ddgs.images(query, max_results=16))
    unique: dict[str, dict] = {}
    for item in results:
        image_url = item.get("image")
        if image_url and image_url.startswith("http"):
            unique.setdefault(image_url, item)
    return sorted(unique.values(), key=source_score)


async def download_image(client: httpx.AsyncClient, image_url: str, target: Path) -> bool:
    try:
        response = await client.get(image_url, follow_redirects=True)
        response.raise_for_status()
    except Exception:
        return False

    content_type = response.headers.get("content-type", "").split(";")[0].lower()
    extension = IMAGE_EXTENSIONS.get(content_type)
    if not extension or len(response.content) < MIN_IMAGE_BYTES:
        return False

    target = target.with_suffix(extension)
    target.write_bytes(response.content)
    return True


async def build_image_set(product: asyncpg.Record) -> tuple[str, list[str], list[str]]:
    product_slug = slugify(product["name"])
    target_dir = PUBLIC_PRODUCTS_DIR / product_slug / "auto"
    target_dir.mkdir(parents=True, exist_ok=True)

    for old_file in target_dir.glob("*"):
        if old_file.is_file():
            old_file.unlink()

    results = search_images(product["name"], product["brand"])
    saved_urls: list[str] = []
    source_urls: list[str] = []

    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(timeout=25, headers=headers) as client:
        for result in results:
            if len(saved_urls) >= MAX_IMAGES_PER_PRODUCT:
                break
            image_url = result["image"]
            filename = "cover" if not saved_urls else f"gallery-{len(saved_urls):02d}"
            target = target_dir / filename
            if not await download_image(client, image_url, target):
                continue
            saved_file = next(target_dir.glob(f"{filename}.*"))
            saved_urls.append(f"/images/products/{product_slug}/auto/{saved_file.name}")
            source_urls.append(result.get("url") or image_url)

    if not saved_urls:
        raise RuntimeError(f"Không tải được ảnh hợp lệ cho {product['name']}.")

    cover = saved_urls[0]
    gallery = saved_urls[1:] or saved_urls[:1]
    return cover, gallery, source_urls


async def target_products(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    rows = await conn.fetch(
        """
        SELECT p.id, p.sku, p.name, b.name AS brand, p.image_url, p.images
        FROM products p
        LEFT JOIN brands b ON b.id = p.brand_id
        WHERE p.deleted_at IS NULL
          AND p.parent_product_id IS NULL
          AND p.status IN ('ACTIVE', 'DRAFT')
        ORDER BY p.name
        """
    )
    return [
        row
        for row in rows
        if not row["image_url"] or images_need_fix(row["images"])
        or local_file_missing(row["image_url"])
        or any(local_file_missing(url) for url in image_values(row["images"]))
    ]


async def update_product(conn: asyncpg.Connection, product: asyncpg.Record) -> None:
    cover, gallery, sources = await build_image_set(product)
    gallery_json = json.dumps(gallery, ensure_ascii=False)

    async with conn.transaction():
        await conn.execute(
            """
            UPDATE products
            SET image_url = $1,
                images = $2::jsonb,
                updated_at = NOW()
            WHERE id = $3
            """,
            cover,
            gallery_json,
            product["id"],
        )
        variant_result = await conn.execute(
            """
            UPDATE product_variants
            SET image_url = COALESCE(NULLIF(image_url, ''), $1),
                images = CASE
                    WHEN images IS NULL
                      OR jsonb_typeof(images) <> 'array'
                      OR jsonb_array_length(images) = 0
                      OR images = to_jsonb('[]'::text)
                    THEN $2::jsonb
                    ELSE images
                END,
                updated_at = NOW()
            WHERE product_id = $3
              AND deleted_at IS NULL
              AND is_active IS TRUE
            """,
            cover,
            gallery_json,
            product["id"],
        )

    print(f"{product['sku']} | {product['name']}: {cover}, {len(gallery)} ảnh gallery, {variant_result}")
    for source in sources:
        print(f"  source: {source}")


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        products = await target_products(conn)
        print(f"Cần cập nhật {len(products)} sản phẩm.")
        for product in products:
            await update_product(conn, product)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
