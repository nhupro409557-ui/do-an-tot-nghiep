from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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
                fs.status,
                (
                    fs.status = 'ACTIVE'
                    AND (fs.starts_at IS NULL OR fs.starts_at <= NOW())
                    AND (fs.ends_at IS NULL OR fs.ends_at >= NOW())
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
            INSERT INTO flash_sales (id, product_id, variant_id, discount_type, discount_value, starts_at, ends_at, status)
            VALUES (:id, :product_id, :variant_id, :discount_type, :discount_value, :starts_at, :ends_at, :status)
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
                status = :status,
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
