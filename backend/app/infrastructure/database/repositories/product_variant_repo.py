import json
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_product_variant_context(session: AsyncSession, product_id: UUID) -> dict | None:
    result = await session.execute(
        text("SELECT options, sku, status, parent_product_id FROM products WHERE id = :product_id"),
        {"product_id": product_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def find_active_variant_by_sku(
    session: AsyncSession,
    *,
    sku: str,
    product_id: UUID,
    parent_product_id: UUID | None,
    exclude_variant_id: UUID | None,
) -> UUID | None:
    result = await session.execute(
        text(
            """
            SELECT pv.id
            FROM product_variants pv
            WHERE pv.sku = :sku
              AND pv.deleted_at IS NULL
              AND pv.status <> 'revision_draft'
              AND pv.product_id <> :product_id
              AND (CAST(:parent_product_id AS UUID) IS NULL OR pv.product_id <> CAST(:parent_product_id AS UUID))
              AND (CAST(:id AS UUID) IS NULL OR pv.id <> CAST(:id AS UUID))
            """
        ),
        {
            "sku": sku,
            "id": exclude_variant_id,
            "product_id": product_id,
            "parent_product_id": parent_product_id,
        },
    )
    return result.scalar()


async def list_active_variant_ids(session: AsyncSession, product_id: UUID) -> list[UUID]:
    result = await session.execute(
        text("SELECT id FROM product_variants WHERE product_id = :product_id AND deleted_at IS NULL"),
        {"product_id": product_id},
    )
    return list(result.scalars().all())


async def update_variant(session: AsyncSession, *, variant_id: UUID, values: dict) -> None:
    await session.execute(
        text(
            """
            UPDATE product_variants
            SET sku = :sku,
                color_name = :color_name,
                color_code = :color_code,
                storage = :storage,
                ram = :ram,
                configuration = :configuration,
                specs = CAST(:specs AS jsonb),
                image_url = :image_url,
                images = CAST(:images AS jsonb),
                price = :price,
                sale_price = :sale_price,
                compare_at_price = :compare_at_price,
                stock_quantity = :stock_quantity,
                is_active = :is_active,
                is_default = :is_default,
                status = :status,
                attributes = CAST(:attributes AS jsonb),
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": variant_id, **values},
    )


async def insert_variant(session: AsyncSession, *, variant_id: UUID, product_id: UUID, values: dict) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_variants (
                id, product_id, sku, color_name, color_code, storage, ram, configuration,
                specs, image_url, images, price, sale_price, compare_at_price, stock_quantity,
                is_active, is_default, status, attributes, parent_variant_id, created_at, updated_at
            )
            VALUES (
                :id, :product_id, :sku, :color_name, :color_code, :storage, :ram, :configuration,
                CAST(:specs AS jsonb), :image_url, CAST(:images AS jsonb), :price, :sale_price, :compare_at_price, :stock_quantity,
                :is_active, :is_default, :status, CAST(:attributes AS jsonb), :parent_variant_id, NOW(), NOW()
            )
            """
        ),
        {"id": variant_id, "product_id": product_id, **values},
    )


async def soft_delete_variants(session: AsyncSession, variant_ids: list[UUID]) -> None:
    if not variant_ids:
        return
    await session.execute(
        text(
            """
            UPDATE product_variants
            SET deleted_at = NOW(),
                status = 'deleted',
                is_active = FALSE
            WHERE id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": variant_ids},
    )


async def update_product_sku(session: AsyncSession, *, product_id: UUID, sku: str) -> None:
    await session.execute(
        text("UPDATE products SET sku = :sku WHERE id = :product_id"),
        {"sku": sku, "product_id": product_id},
    )


async def get_variant_for_delete(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID,
) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT id, is_default, sku
            FROM product_variants
            WHERE id = :variant_id AND product_id = :product_id AND deleted_at IS NULL
            """
        ),
        {"variant_id": variant_id, "product_id": product_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def soft_delete_variant(session: AsyncSession, variant_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE product_variants
            SET deleted_at = NOW(),
                status = 'deleted',
                is_active = FALSE,
                is_default = FALSE,
                updated_at = NOW()
            WHERE id = :variant_id
            """
        ),
        {"variant_id": variant_id},
    )


async def get_next_default_variant(session: AsyncSession, product_id: UUID) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT id, sku
            FROM product_variants
            WHERE product_id = :product_id AND deleted_at IS NULL
            ORDER BY created_at ASC
            LIMIT 1
            """
        ),
        {"product_id": product_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def mark_variant_default(session: AsyncSession, variant_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE product_variants
            SET is_default = TRUE,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": variant_id},
    )


async def update_product_sku_with_timestamp(session: AsyncSession, *, product_id: UUID, sku: str) -> None:
    await session.execute(
        text(
            """
            UPDATE products
            SET sku = :sku,
                updated_at = NOW()
            WHERE id = :product_id
            """
        ),
        {"sku": sku, "product_id": product_id},
    )


def json_param(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)
