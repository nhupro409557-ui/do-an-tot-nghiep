from __future__ import annotations

import json
import pathlib
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import asyncpg
import cocoindex as coco
from cocoindex.connectors import localfs, postgres

from app.config import settings


DEFAULT_OUTPUT_DIR = pathlib.Path("var/cocoindex/catalog_markdown")


@dataclass(frozen=True)
class SourceProduct:
    id: UUID
    sku: str | None
    name: str
    slug: str
    category: str
    brand: str
    description: str | None
    specifications: dict | str | None
    price: Decimal
    sale_price: Decimal | None
    stock_quantity: int
    warranty_period: int
    rating: Decimal | None
    review_count: int
    favorite_count: int
    is_featured: bool
    status: str
    updated_at: datetime
    deleted_at: datetime | None


def normalize_asyncpg_dsn(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def safe_filename(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-._")
    return normalized.lower() or "product"


def money_text(value: Decimal | None) -> str:
    if value is None:
        return "Không có"
    return f"{int(value):,}".replace(",", ".") + "đ"


def product_filename(product: SourceProduct) -> str:
    return f"{safe_filename(product.slug)}-{product.id}.md"


def normalize_specifications(value: dict | str | None) -> dict | list | str:
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return value
        return loaded if isinstance(loaded, (dict, list)) else value
    return value


def product_to_markdown(product: SourceProduct) -> str:
    specifications = json.dumps(
        normalize_specifications(product.specifications),
        ensure_ascii=False,
        indent=2,
    )
    description = (product.description or "").strip() or "Chưa có mô tả."
    sale_line = f"- Giá khuyến mãi: {money_text(product.sale_price)}" if product.sale_price else ""
    featured = "Có" if product.is_featured else "Không"
    updated_at = product.updated_at.isoformat()

    lines = [
        f"# {product.name}",
        "",
        "## Thông tin chính",
        "",
        f"- ID: {product.id}",
        f"- SKU: {product.sku or 'Không có'}",
        f"- Slug: {product.slug}",
        f"- Thương hiệu: {product.brand}",
        f"- Danh mục: {product.category}",
        f"- Giá niêm yết: {money_text(product.price)}",
    ]
    if sale_line:
        lines.append(sale_line)
    lines.extend(
        [
            f"- Tồn kho: {product.stock_quantity}",
            f"- Bảo hành: {product.warranty_period} tháng",
            f"- Đánh giá: {product.rating or 0} ({product.review_count} lượt)",
            f"- Lượt yêu thích: {product.favorite_count}",
            f"- Sản phẩm nổi bật: {featured}",
            f"- Cập nhật lúc: {updated_at}",
            "",
            "## Mô tả",
            "",
            description,
            "",
            "## Thông số kỹ thuật",
            "",
            "```json",
            specifications,
            "```",
            "",
        ]
    )
    return "\n".join(lines)


@coco.fn(memo=True, version=2)
def process_product(product: SourceProduct, outdir: pathlib.Path) -> None:
    if product.status != "ACTIVE" or product.deleted_at is not None:
        return
    localfs.declare_file(
        outdir / product_filename(product),
        product_to_markdown(product),
        create_parent_dirs=True,
    )


@coco.fn
async def app_main(database_url: str, outdir: pathlib.Path) -> None:
    pool = await asyncpg.create_pool(normalize_asyncpg_dsn(database_url))
    try:
        source = postgres.PgTableSource(
            pool,
            table_name="products",
            columns=[
                "id",
                "sku",
                "name",
                "slug",
                "category",
                "brand",
                "description",
                "specifications",
                "price",
                "sale_price",
                "stock_quantity",
                "warranty_period",
                "rating",
                "review_count",
                "favorite_count",
                "is_featured",
                "status",
                "updated_at",
                "deleted_at",
            ],
            row_type=SourceProduct,
        )
        async for product in source.fetch_rows():
            await coco.mount(
                coco.component_subpath("product", str(product.id)),
                process_product,
                product,
                outdir,
            )
    finally:
        await pool.close()


app = coco.App(
    "CatalogMarkdownIndex",
    app_main,
    database_url=settings.database_url,
    outdir=DEFAULT_OUTPUT_DIR,
)
