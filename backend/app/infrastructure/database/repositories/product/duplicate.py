import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_product_source_for_duplicate(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(text("SELECT id, name FROM products WHERE id = :id"), {"id": product_id})
    ).mappings().first()
    return dict(row) if row else None


async def duplicate_product_record(
    session: AsyncSession,
    *,
    new_id: UUID,
    source_id: UUID,
    sku: str,
    slug: str,
) -> bool:
    result = await session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, category_id, subcategory_id, brand_id,
                description, specifications, seo_metadata, sales_config, price, sale_price, stock_quantity, image_url,
                images, video_url, colors, capacities, promotions, status, is_featured, is_flash_sale, options
            )
            SELECT
                :new_id,
                :sku,
                CONCAT(name, ' (Copy)'),
                :slug,
                category,
                brand,
                category_id,
                subcategory_id,
                brand_id,
                description,
                specifications,
                seo_metadata,
                sales_config,
                price,
                sale_price,
                0,
                image_url,
                images,
                video_url,
                colors,
                capacities,
                promotions,
                'DRAFT',
                is_featured,
                is_flash_sale,
                options
            FROM products
            WHERE id = :source_id
            RETURNING id::text
            """
        ),
        {"new_id": new_id, "source_id": source_id, "sku": sku, "slug": slug},
    )
    return bool(result.first())


async def duplicate_product_variants(session: AsyncSession, *, new_id: UUID, source_id: UUID, suffix: str) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_variants (
                id, product_id, sku, color_name, color_code, storage, ram, configuration,
                specs, image_url, images, price, sale_price, compare_at_price, stock_quantity,
                is_active, is_default, status, attributes
            )
            SELECT
                gen_random_uuid(),
                :new_id,
                LEFT(CONCAT(sku, '-COPY-', CAST(:suffix AS TEXT)), 120),
                color_name,
                color_code,
                storage,
                ram,
                configuration,
                specs,
                image_url,
                images,
                price,
                sale_price,
                compare_at_price,
                0,
                is_active,
                is_default,
                status,
                attributes
            FROM product_variants
            WHERE product_id = :source_id AND is_active = TRUE AND deleted_at IS NULL
            """
        ),
        {"new_id": new_id, "source_id": source_id, "suffix": suffix},
    )


async def duplicate_product_bundles(session: AsyncSession, *, new_id: UUID, source_id: UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_bundles (product_id, bundled_product_id)
            SELECT :new_id, bundled_product_id
            FROM product_bundles
            WHERE product_id = :source_id
            ON CONFLICT DO NOTHING
            """
        ),
        {"new_id": new_id, "source_id": source_id},
    )


async def duplicate_product_accessories(session: AsyncSession, *, new_id: UUID, source_id: UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_accessories (product_id, accessory_product_id)
            SELECT :new_id, accessory_product_id
            FROM product_accessories
            WHERE product_id = :source_id
            ON CONFLICT DO NOTHING
            """
        ),
        {"new_id": new_id, "source_id": source_id},
    )
