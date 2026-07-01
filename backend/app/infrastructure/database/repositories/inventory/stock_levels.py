from .stock_mutation_common import *

async def delete_old_inventory_idempotency(session: AsyncSession) -> None:
    await session.execute(text("DELETE FROM product_inventory_idempotency WHERE created_at < NOW() - INTERVAL '30 days'"))


async def get_inventory_idempotency_response(session: AsyncSession, key: str) -> dict | None:
    row = (
        await session.execute(
            text("SELECT response_payload FROM product_inventory_idempotency WHERE idempotency_key = :key"),
            {"key": key},
        )
    ).mappings().first()
    return dict(row["response_payload"]) if row else None


async def list_product_variant_ids(session: AsyncSession, product_id: UUID) -> list[dict]:
    rows = (
        await session.execute(
            text(
                """
                SELECT id
                FROM product_variants
                WHERE product_id = :product_id
                  AND deleted_at IS NULL
                  AND is_active = TRUE
                  AND COALESCE(status, 'active') NOT IN ('deleted', 'archived')
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def get_product_receipt_eligibility_for_update(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    p.id,
                    p.name,
                    p.sku,
                    p.status,
                    p.deleted_at,
                    p.hidden_by_category,
                    p.hidden_by_brand,
                    EXISTS (
                        SELECT 1
                        FROM products revision
                        WHERE revision.parent_product_id = p.id
                          AND revision.deleted_at IS NULL
                          AND revision.status IN ('REVISION_DRAFT', 'PENDING')
                    ) AS has_pending_revision
                FROM products p
                WHERE p.id = :product_id
                FOR UPDATE
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_variant_inventory_for_update(session: AsyncSession, *, product_id: UUID, variant_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, stock_quantity, sku
                FROM product_variants
                WHERE id = :variant_id
                  AND product_id = :product_id
                  AND deleted_at IS NULL
                  AND is_active = TRUE
                  AND COALESCE(status, 'active') NOT IN ('deleted', 'archived')
                FOR UPDATE
                """
            ),
            {"variant_id": variant_id, "product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_product_stock_for_update(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, stock_quantity, sku
                FROM products
                WHERE id = :product_id
                FOR UPDATE
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_product_stock(session: AsyncSession, *, product_id: UUID, quantity: int) -> None:
    await session.execute(
        text("UPDATE products SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
        {"id": product_id, "quantity": quantity},
    )


async def list_existing_imeis(session: AsyncSession, imeis: list[str]) -> list[str]:
    if not imeis:
        return []
    rows = (
        await session.execute(
            text("SELECT imei FROM product_imeis WHERE imei = ANY(:imeis)"),
            {"imeis": imeis},
        )
    ).mappings().all()
    return [str(row["imei"]) for row in rows]


async def list_existing_serial_numbers(session: AsyncSession, serial_numbers: list[str], product_id: UUID | None = None) -> list[str]:
    if not serial_numbers:
        return []
    product_filter = "AND product_id = :product_id" if product_id else ""
    rows = (
        await session.execute(
            text(f"""
                SELECT serial_number
                FROM product_serial_numbers
                WHERE serial_number = ANY(:serial_numbers)
                {product_filter}
            """),
            {"serial_numbers": serial_numbers, "product_id": product_id},
        )
    ).mappings().all()
    return [str(row["serial_number"]) for row in rows]


async def update_variant_stock(session: AsyncSession, *, variant_id: UUID, quantity: int) -> None:
    await session.execute(
        text("UPDATE product_variants SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
        {"id": variant_id, "quantity": quantity},
    )
