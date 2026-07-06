from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


ACTIVE_WINDOW_SQL = """
    status = 'ACTIVE'
    AND (starts_at IS NULL OR starts_at <= NOW())
    AND (ends_at IS NULL OR ends_at >= NOW())
    AND (quantity_limit IS NULL OR sold_quantity < quantity_limit)
"""


async def get_target_current_price(session: AsyncSession, product_id: UUID, variant_id: UUID | None) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT p.id,
                       COALESCE(NULLIF(pv.sale_price, 0), pv.price, NULLIF(p.sale_price, 0), p.price, 0) AS current_price
                FROM products p
                LEFT JOIN product_variants pv
                  ON pv.id = :variant_id
                 AND pv.product_id = p.id
                 AND pv.is_active = TRUE
                 AND pv.deleted_at IS NULL
                WHERE p.id = :product_id
                  AND p.deleted_at IS NULL
                  AND (:variant_id IS NULL OR pv.id IS NOT NULL)
                """
            ),
            {"product_id": product_id, "variant_id": variant_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def find_overlapping_flash_sale(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    starts_at,
    ends_at,
    exclude_id: UUID | None = None,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id::text, starts_at, ends_at
                FROM flash_sales
                WHERE status = 'ACTIVE'
                  AND product_id = :product_id
                  AND variant_id IS NOT DISTINCT FROM :variant_id
                  AND (
                      CAST(:exclude_id AS UUID) IS NULL
                      OR id <> CAST(:exclude_id AS UUID)
                  )
                  AND tstzrange(starts_at, ends_at, '[)')
                      && tstzrange(
                          CAST(:starts_at AS TIMESTAMPTZ),
                          CAST(:ends_at AS TIMESTAMPTZ),
                          '[)'
                      )
                LIMIT 1
                """
            ),
            {
                "product_id": product_id,
                "variant_id": variant_id,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "exclude_id": exclude_id,
            },
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_flash_sale_sold_quantity(session: AsyncSession, sale_id: UUID) -> int | None:
    value = await session.scalar(
        text("SELECT sold_quantity FROM flash_sales WHERE id = :id"),
        {"id": sale_id},
    )
    return None if value is None else int(value)


async def list_flash_sale_rows(session: AsyncSession):
    return await session.execute(
        text(
            """
            SELECT
                fs.id::text AS id,
                fs.product_id::text AS "productId",
                fs.variant_id::text AS "variantId",
                p.name AS "productName",
                p.sku AS "productSku",
                pv.sku AS "variantSku",
                COALESCE(pv.configuration, pv.storage, pv.color_name) AS "variantName",
                COALESCE(pv.image_url, p.image_url) AS "imageUrl",
                COALESCE(NULLIF(pv.sale_price, 0), pv.price, NULLIF(p.sale_price, 0), p.price, 0) AS "currentPrice",
                fs.discount_type AS "discountType",
                fs.discount_value AS "discountValue",
                fs.starts_at AS "startsAt",
                fs.ends_at AS "endsAt",
                fs.quantity_limit AS "quantityLimit",
                fs.sold_quantity AS "soldQuantity",
                GREATEST(fs.quantity_limit - fs.sold_quantity, 0) AS "remainingQuantity",
                fs.quota_exhausted_at AS "quotaExhaustedAt",
                fs.status,
                (
                    fs.status = 'ACTIVE'
                    AND (fs.starts_at IS NULL OR fs.starts_at <= NOW())
                    AND (fs.ends_at IS NULL OR fs.ends_at >= NOW())
                    AND (fs.quantity_limit IS NULL OR fs.sold_quantity < fs.quantity_limit)
                ) AS "isRunning"
            FROM flash_sales fs
            JOIN products p ON p.id = fs.product_id
            LEFT JOIN product_variants pv ON pv.id = fs.variant_id
            WHERE p.deleted_at IS NULL
            ORDER BY "isRunning" DESC, fs.updated_at DESC
            """
        )
    )


async def insert_flash_sale(session: AsyncSession, params: dict) -> None:
    await session.execute(
        text(
            """
            INSERT INTO flash_sales (
                id, product_id, variant_id, discount_type, discount_value,
                starts_at, ends_at, quantity_limit, status
            )
            VALUES (
                :id, :product_id, :variant_id, :discount_type, :discount_value,
                :starts_at, :ends_at, :quantity_limit, :status
            )
            """
        ),
        params,
    )


async def update_flash_sale(session: AsyncSession, params: dict) -> int:
    result = await session.execute(
        text(
            """
            UPDATE flash_sales
            SET product_id = :product_id,
                variant_id = :variant_id,
                discount_type = :discount_type,
                discount_value = :discount_value,
                starts_at = :starts_at,
                ends_at = :ends_at,
                quantity_limit = :quantity_limit,
                status = :status,
                quota_exhausted_at = CASE WHEN :status = 'ACTIVE' THEN NULL ELSE quota_exhausted_at END,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        params,
    )
    return int(result.rowcount or 0)


async def delete_flash_sale(session: AsyncSession, sale_id: UUID) -> int:
    result = await session.execute(text("DELETE FROM flash_sales WHERE id = :id"), {"id": sale_id})
    return int(result.rowcount or 0)


async def reserve_flash_sale_quantity(session: AsyncSession, *, sale_id: UUID, quantity: int) -> dict | None:
    if quantity <= 0:
        return None
    row = (
        await session.execute(
            text(
                """
                UPDATE flash_sales
                SET sold_quantity = sold_quantity + :quantity,
                    status = CASE
                        WHEN quantity_limit IS NOT NULL AND sold_quantity + :quantity >= quantity_limit
                        THEN 'INACTIVE'
                        ELSE status
                    END,
                    quota_exhausted_at = CASE
                        WHEN quantity_limit IS NOT NULL AND sold_quantity + :quantity >= quantity_limit
                        THEN COALESCE(quota_exhausted_at, NOW())
                        ELSE quota_exhausted_at
                    END,
                    updated_at = NOW()
                WHERE id = :sale_id
                  AND status = 'ACTIVE'
                  AND (starts_at IS NULL OR starts_at <= NOW())
                  AND (ends_at IS NULL OR ends_at >= NOW())
                  AND (quantity_limit IS NULL OR sold_quantity + :quantity <= quantity_limit)
                RETURNING id::text AS id,
                          quantity_limit AS "quantityLimit",
                          sold_quantity AS "soldQuantity",
                          status,
                          quota_exhausted_at AS "quotaExhaustedAt"
                """
            ),
            {"sale_id": sale_id, "quantity": quantity},
        )
    ).mappings().first()
    return dict(row) if row else None


async def release_order_flash_sale_quantities(session: AsyncSession, order_id: UUID) -> None:
    rows = (
        await session.execute(
            text(
                """
                SELECT flash_sale_id, SUM(flash_sale_quantity)::int AS quantity
                FROM order_items
                WHERE order_id = :order_id
                  AND flash_sale_id IS NOT NULL
                  AND flash_sale_quantity > 0
                  AND flash_sale_released_at IS NULL
                GROUP BY flash_sale_id
                """
            ),
            {"order_id": order_id},
        )
    ).mappings().all()
    if not rows:
        return

    for row in rows:
        await session.execute(
            text(
                """
                WITH next_values AS (
                    SELECT
                        id,
                        product_id,
                        variant_id,
                        starts_at,
                        ends_at,
                        GREATEST(sold_quantity - :quantity, 0) AS next_sold_quantity,
                        quantity_limit,
                        quota_exhausted_at,
                        ends_at AS sale_ends_at
                    FROM flash_sales
                    WHERE id = :sale_id
                    FOR UPDATE
                ),
                reactivation_check AS (
                    SELECT
                        nv.*,
                        NOT EXISTS (
                            SELECT 1
                            FROM flash_sales other
                            WHERE other.id <> nv.id
                              AND other.status = 'ACTIVE'
                              AND other.product_id = nv.product_id
                              AND other.variant_id IS NOT DISTINCT FROM nv.variant_id
                              AND tstzrange(other.starts_at, other.ends_at, '[)')
                                  && tstzrange(nv.starts_at, nv.ends_at, '[)')
                        ) AS can_reactivate
                    FROM next_values nv
                )
                UPDATE flash_sales fs
                SET sold_quantity = rc.next_sold_quantity,
                    status = CASE
                        WHEN fs.status = 'INACTIVE'
                         AND rc.quota_exhausted_at IS NOT NULL
                         AND (rc.quantity_limit IS NULL OR rc.next_sold_quantity < rc.quantity_limit)
                         AND (rc.sale_ends_at IS NULL OR rc.sale_ends_at >= NOW())
                         AND rc.can_reactivate
                        THEN 'ACTIVE'
                        ELSE fs.status
                    END,
                    quota_exhausted_at = CASE
                        WHEN rc.quota_exhausted_at IS NOT NULL
                         AND (rc.quantity_limit IS NULL OR rc.next_sold_quantity < rc.quantity_limit)
                         AND rc.can_reactivate
                        THEN NULL
                        ELSE fs.quota_exhausted_at
                    END,
                    updated_at = NOW()
                FROM reactivation_check rc
                WHERE fs.id = rc.id
                """
            ),
            {"sale_id": row["flash_sale_id"], "quantity": int(row["quantity"] or 0)},
        )

    await session.execute(
        text(
            """
            UPDATE order_items
            SET flash_sale_released_at = NOW()
            WHERE order_id = :order_id
              AND flash_sale_id IS NOT NULL
              AND flash_sale_quantity > 0
              AND flash_sale_released_at IS NULL
            """
        ),
        {"order_id": order_id},
    )
