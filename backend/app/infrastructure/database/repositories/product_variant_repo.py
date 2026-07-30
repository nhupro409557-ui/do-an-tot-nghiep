import json
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_product_variant_context(session: AsyncSession, product_id: UUID) -> dict | None:
    result = await session.execute(
        text("SELECT options, sku, status, parent_product_id FROM products WHERE id = :product_id FOR UPDATE"),
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


async def list_variant_integrity_snapshots(session: AsyncSession, product_id: UUID) -> dict[UUID, dict]:
    result = await session.execute(
        text(
            """
            SELECT id, sku, color_name, storage, ram, configuration, specs, attributes, stock_quantity
            FROM product_variants
            WHERE product_id = :product_id
              AND deleted_at IS NULL
            """
        ),
        {"product_id": product_id},
    )
    return {row["id"]: dict(row) for row in result.mappings().all()}


async def list_bound_variant_ids(session: AsyncSession, variant_ids: list[UUID]) -> set[UUID]:
    if not variant_ids:
        return set()
    optional_tables = {
        "inventory_document_lines",
        "inventory_transactions",
        "inventory_reservations",
        "inventory_lots",
        "inventory_lot_movements",
        "inventory_adjustment_logs",
        "product_imeis",
        "product_serial_numbers",
        "used_devices",
        "used_device_intake_requests",
        "flash_sales",
    }
    table_result = await session.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN :table_names
            """
        ).bindparams(bindparam("table_names", expanding=True)),
        {"table_names": sorted(optional_tables)},
    )
    existing_tables = set(table_result.scalars().all())
    optional_checks = []
    if "inventory_document_lines" in existing_tables:
        optional_checks.append("EXISTS (SELECT 1 FROM inventory_document_lines idl WHERE idl.variant_id = tv.id)")
    if "inventory_transactions" in existing_tables:
        optional_checks.append("EXISTS (SELECT 1 FROM inventory_transactions it WHERE it.variant_id = tv.id)")
    if "inventory_reservations" in existing_tables:
        optional_checks.append(
            "EXISTS (SELECT 1 FROM inventory_reservations ir WHERE ir.variant_id = tv.id AND ir.status IN ('ACTIVE', 'LOCKED'))"
        )
    if "inventory_lots" in existing_tables:
        optional_checks.append("EXISTS (SELECT 1 FROM inventory_lots ilot WHERE ilot.variant_id = tv.id)")
    if "inventory_lot_movements" in existing_tables:
        optional_checks.append(
            "EXISTS (SELECT 1 FROM inventory_lot_movements ilm JOIN inventory_lots ilot ON ilot.id = ilm.lot_id WHERE ilot.variant_id = tv.id)"
        )
    if "inventory_adjustment_logs" in existing_tables:
        optional_checks.append("EXISTS (SELECT 1 FROM inventory_adjustment_logs ial WHERE ial.variant_id = tv.id)")
    if "product_imeis" in existing_tables:
        optional_checks.append("EXISTS (SELECT 1 FROM product_imeis pi WHERE pi.variant_id = tv.id)")
    if "product_serial_numbers" in existing_tables:
        optional_checks.append("EXISTS (SELECT 1 FROM product_serial_numbers psn WHERE psn.variant_id = tv.id)")
    if "used_devices" in existing_tables:
        optional_checks.append("EXISTS (SELECT 1 FROM used_devices ud WHERE ud.variant_id = tv.id)")
    if "used_device_intake_requests" in existing_tables:
        optional_checks.append("EXISTS (SELECT 1 FROM used_device_intake_requests udi WHERE udi.variant_id = tv.id)")
    if "flash_sales" in existing_tables:
        optional_checks.append(
            "EXISTS (SELECT 1 FROM flash_sales fs WHERE fs.variant_id = tv.id AND fs.status = 'ACTIVE')"
        )
    optional_sql = "\n               OR ".join(optional_checks)
    if optional_sql:
        optional_sql = "\n               OR " + optional_sql
    result = await session.execute(
        text(
            f"""
            WITH target_variants AS (
                SELECT unnest(CAST(:variant_ids AS uuid[])) AS id
            )
            SELECT tv.id
            FROM target_variants tv
            WHERE EXISTS (
                    SELECT 1 FROM inventory_levels il
                    WHERE il.variant_id = tv.id
                      AND (il.on_hand_quantity <> 0 OR il.reserved_quantity <> 0)
                )
               OR EXISTS (SELECT 1 FROM order_items oi WHERE oi.variant_id = tv.id)
               {optional_sql}
            """
        ),
        {"variant_ids": variant_ids},
    )
    return set(result.scalars().all())


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


async def update_product_sku(session: AsyncSession, *, product_id: UUID, sku: str) -> int:
    result = await session.execute(
        text(
            """
            UPDATE products
            SET sku = :sku
            WHERE id = :product_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM products other
                  WHERE other.id <> :product_id
                    AND other.sku = :sku
                    AND other.deleted_at IS NULL
              )
            """
        ),
        {"sku": sku, "product_id": product_id},
    )
    return int(result.rowcount or 0)


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
            FOR UPDATE
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


async def update_product_sku_with_timestamp(session: AsyncSession, *, product_id: UUID, sku: str) -> int:
    result = await session.execute(
        text(
            """
            UPDATE products
            SET sku = :sku,
                updated_at = NOW()
            WHERE id = :product_id
              AND NOT EXISTS (
                  SELECT 1
                  FROM products other
                  WHERE other.id <> :product_id
                    AND other.sku = :sku
                    AND other.deleted_at IS NULL
              )
            """
        ),
        {"sku": sku, "product_id": product_id},
    )
    return int(result.rowcount or 0)


def json_param(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)
