import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def insert_product_record(
    session: AsyncSession,
    *,
    product_id: UUID,
    sku: str,
    name: str,
    slug: str,
    category: str,
    brand: str,
    category_id: UUID | None,
    subcategory_id: UUID | None,
    brand_id: UUID | None,
    description: str,
    specifications: dict,
    seo_metadata: dict,
    sales_config: dict,
    price: float,
    sale_price: float | None,
    stock_quantity: int,
    image_url: str | None,
    images: list[str],
    video_url: str | None,
    status: str,
    is_featured: bool,
    is_flash_sale: bool,
    options: list[dict],
    parent_product_id: UUID | None = None,
) -> None:
    revision_columns = ", parent_product_id" if parent_product_id else ""
    revision_values = ", :parent_product_id" if parent_product_id else ""
    await session.execute(
        text(
            f"""
            INSERT INTO products (
                id{revision_columns}, sku, name, slug, category, brand, category_id, subcategory_id, brand_id,
                description, specifications, seo_metadata, sales_config, price, sale_price, stock_quantity, image_url,
                images, video_url, colors, capacities, promotions, status, is_featured, is_flash_sale, options
            )
            VALUES (
                :id{revision_values}, :sku, :name, :slug, :category, :brand, :category_id, :subcategory_id, :brand_id,
                :description, CAST(:specifications AS jsonb), CAST(:seo_metadata AS jsonb), CAST(:sales_config AS jsonb),
                :price, :sale_price, :stock_quantity, :image_url, CAST(:images AS jsonb), :video_url,
                '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, :status, :is_featured, :is_flash_sale,
                CAST(:options AS jsonb)
            )
            """
        ),
        {
            "id": product_id,
            "parent_product_id": parent_product_id,
            "sku": sku,
            "name": name,
            "slug": slug,
            "category": category,
            "brand": brand,
            "category_id": category_id,
            "subcategory_id": subcategory_id,
            "brand_id": brand_id,
            "description": description,
            "specifications": json.dumps(specifications),
            "seo_metadata": json.dumps(seo_metadata),
            "sales_config": json.dumps(sales_config),
            "price": price,
            "sale_price": sale_price,
            "stock_quantity": stock_quantity,
            "image_url": image_url,
            "images": json.dumps(images),
            "video_url": video_url,
            "status": status,
            "is_featured": is_featured,
            "is_flash_sale": is_flash_sale,
            "options": json.dumps(options),
        },
    )


async def get_product_current_for_update(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text("SELECT status, version, updated_at, name, price, sale_price, stock_quantity, category_id, subcategory_id FROM products WHERE id = :id"),
            {"id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def product_visibility_blocker(
    session: AsyncSession,
    *,
    product_id: UUID | None = None,
    category_id: UUID | None = None,
    subcategory_id: UUID | None = None,
    brand_id: UUID | None = None,
) -> str | None:
    row = (
        await session.execute(
            text(
                """
                WITH product_scope AS (
                    SELECT
                        COALESCE(CAST(:category_id AS uuid), p.category_id) AS category_id,
                        COALESCE(CAST(:subcategory_id AS uuid), p.subcategory_id) AS subcategory_id,
                        COALESCE(CAST(:brand_id AS uuid), p.brand_id) AS brand_id
                    FROM (SELECT 1) seed
                    LEFT JOIN products p ON p.id = CAST(:product_id AS uuid)
                )
                SELECT
                    category.name AS category_name,
                    category.status AS category_status,
                    category.is_active AS category_is_active,
                    COALESCE(category.is_deleted, FALSE) AS category_is_deleted,
                    brand.name AS brand_name,
                    brand.is_active AS brand_is_active
                FROM product_scope scope
                LEFT JOIN categories category ON category.id = COALESCE(scope.subcategory_id, scope.category_id)
                LEFT JOIN brands brand ON brand.id = scope.brand_id
                """
            ),
            {
                "product_id": product_id,
                "category_id": category_id,
                "subcategory_id": subcategory_id,
                "brand_id": brand_id,
            },
        )
    ).mappings().first()
    if not row:
        return None
    if row["category_name"] and (
        row["category_status"] != "ACTIVE"
        or row["category_is_active"] is not True
        or row["category_is_deleted"] is True
    ):
        return f"Danh mục {row['category_name']} đang ẩn. Hãy bật danh mục trước khi bật sản phẩm."
    if row["brand_name"] and row["brand_is_active"] is not True:
        return f"Thương hiệu {row['brand_name']} đang ẩn. Hãy bật thương hiệu trước khi bật sản phẩm."
    return None


async def update_product_record(
    session: AsyncSession,
    *,
    product_id: UUID,
    name: str,
    category: str,
    brand: str,
    category_id: UUID | None,
    subcategory_id: UUID | None,
    brand_id: UUID | None,
    description: str,
    specifications: dict,
    seo_metadata: dict,
    sales_config: dict,
    price: float,
    sale_price: float | None,
    stock_quantity: int,
    image_url: str | None,
    images: list[str],
    video_url: str | None,
    options: list[dict],
    status: str,
    is_featured: bool,
    is_flash_sale: bool,
) -> int:
    result = await session.execute(
        text(
            """
            UPDATE products
            SET name = :name,
                category = :category,
                brand = :brand,
                category_id = :category_id,
                subcategory_id = :subcategory_id,
                brand_id = :brand_id,
                description = :description,
                specifications = CAST(:specifications AS jsonb),
                seo_metadata = CAST(:seo_metadata AS jsonb),
                sales_config = CAST(:sales_config AS jsonb),
                price = :price,
                sale_price = :sale_price,
                stock_quantity = :stock_quantity,
                image_url = :image_url,
                images = CAST(:images AS jsonb),
                video_url = :video_url,
                options = CAST(:options AS jsonb),
                status = :status,
                is_featured = :is_featured,
                is_flash_sale = :is_flash_sale,
                version = version + 1,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": product_id,
            "name": name,
            "category": category,
            "brand": brand,
            "category_id": category_id,
            "subcategory_id": subcategory_id,
            "brand_id": brand_id,
            "description": description,
            "specifications": json.dumps(specifications),
            "seo_metadata": json.dumps(seo_metadata),
            "sales_config": json.dumps(sales_config),
            "price": price,
            "sale_price": sale_price,
            "stock_quantity": stock_quantity,
            "image_url": image_url,
            "images": json.dumps(images),
            "video_url": video_url,
            "options": json.dumps(options),
            "status": status,
            "is_featured": is_featured,
            "is_flash_sale": is_flash_sale,
        },
    )
    return int(result.rowcount or 0)


async def deactivate_product_variants(session: AsyncSession, product_id: UUID) -> None:
    await session.execute(
        text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id = :product_id"),
        {"product_id": product_id},
    )
