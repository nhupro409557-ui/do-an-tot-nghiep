import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_product_catalog_kpis(session: AsyncSession) -> dict:
    result = await session.execute(
        text(
            """
            SELECT
                AVG(EXTRACT(EPOCH FROM (active_product.updated_at - draft_product.created_at)) / 3600) AS time_to_market_hours,
                COUNT(*) FILTER (WHERE active_product.status = 'DRAFT' AND active_product.updated_at < NOW() - INTERVAL '30 days') AS orphaned_products,
                COUNT(*) FILTER (WHERE active_product.status = 'INACTIVE') AS inactive_products,
                COUNT(*) FILTER (WHERE active_product.status = 'ACTIVE') AS active_products
            FROM products active_product
            LEFT JOIN products draft_product ON draft_product.id = active_product.id
            """
        )
    )
    row = dict(result.mappings().one())
    import_jobs = (
        await session.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(imported_rows), 0) AS imported_rows,
                    COALESCE(SUM(total_rows), 0) AS total_rows
                FROM product_import_jobs
                WHERE status IN ('COMPLETED', 'FAILED')
                """
            )
        )
    ).mappings().one()
    total_rows = int(import_jobs["total_rows"] or 0)
    return {
        "timeToMarketHours": float(row["time_to_market_hours"] or 0),
        "catalogAccuracyRate": 1 - (int(row["inactive_products"] or 0) / max(int(row["active_products"] or 0) + int(row["inactive_products"] or 0), 1)),
        "orphanedProducts": int(row["orphaned_products"] or 0),
        "importSuccessRate": (int(import_jobs["imported_rows"] or 0) / total_rows) if total_rows else 1,
    }


async def list_product_audit_logs(session: AsyncSession, product_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, product_id::text AS "productId", actor_id::text AS "actorId",
                   action, old_value AS "oldValue", new_value AS "newValue", created_at AS "createdAt"
            FROM product_audit_logs
            WHERE product_id = :product_id
            ORDER BY created_at DESC
            LIMIT 100
            """
        ),
        {"product_id": product_id},
    )
    return [dict(row._mapping) for row in result]


async def delete_product_accessories(session: AsyncSession, product_id: UUID) -> None:
    await session.execute(
        text("DELETE FROM product_accessories WHERE product_id = :product_id"),
        {"product_id": product_id},
    )


async def insert_product_accessory(session: AsyncSession, *, product_id: UUID, accessory_id: UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_accessories (product_id, accessory_product_id)
            VALUES (:product_id, :accessory_id)
            ON CONFLICT DO NOTHING
            """
        ),
        {"product_id": product_id, "accessory_id": accessory_id},
    )


async def delete_product_attached_services(session: AsyncSession, product_id: UUID) -> None:
    await session.execute(
        text("DELETE FROM product_attached_services WHERE product_id = :product_id"),
        {"product_id": product_id},
    )


async def get_active_attached_service_group(session: AsyncSession, service_id: UUID) -> dict | None:
    result = await session.execute(
        text("SELECT service_type, attribute_group FROM attached_services WHERE id = :id AND is_active = TRUE"),
        {"id": service_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def upsert_product_attached_service(session: AsyncSession, *, product_id: UUID, service_id: UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_attached_services (product_id, service_id, override_price)
            VALUES (:product_id, :service_id, :override_price)
            ON CONFLICT (product_id, service_id)
            DO UPDATE SET override_price = EXCLUDED.override_price
            """
        ),
        {
            "product_id": product_id,
            "service_id": service_id,
            "override_price": None,
        },
    )


async def list_product_bundle_rows(session: AsyncSession, product_ids: list[UUID]) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT pb.product_id::text AS product_id, p.sku
            FROM product_bundles pb
            JOIN products p ON p.id = pb.bundled_product_id
            WHERE pb.product_id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": product_ids},
    )
    return [dict(row._mapping) for row in result]


async def list_product_accessory_rows(session: AsyncSession, product_ids: list[UUID]) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                pa.product_id::text AS product_id,
                p.id::text AS accessory_id,
                p.sku,
                p.name,
                p.image_url AS image_url,
                p.image_url AS "imageUrl",
                COALESCE(NULLIF(p.price, 0), vp.min_price, 0) AS price,
                COALESCE(NULLIF(p.sale_price, 0), vp.min_sale_price) AS "discountPrice",
                COALESCE(NULLIF(p.sale_price, 0), vp.min_sale_price) AS "salePrice",
                GREATEST(COALESCE(vs.variant_stock, 0), COALESCE(p.stock_quantity, 0)) AS stock_quantity,
                GREATEST(COALESCE(vs.variant_stock, 0), COALESCE(p.stock_quantity, 0)) AS "stockQuantity",
                p.status
            FROM product_accessories pa
            JOIN products p ON p.id = pa.accessory_product_id
            LEFT JOIN (
                SELECT product_id, SUM(stock_quantity) AS variant_stock
                FROM product_variants
                WHERE is_active = TRUE
                  AND deleted_at IS NULL
                  AND status NOT IN ('deleted', 'archived', 'inactive', 'discontinued')
                GROUP BY product_id
            ) vs ON vs.product_id = p.id
            LEFT JOIN (
                SELECT product_id,
                       MIN(NULLIF(price, 0)) AS min_price,
                       MIN(COALESCE(NULLIF(sale_price, 0), NULLIF(price, 0))) AS min_sale_price
                FROM product_variants
                WHERE is_active = TRUE
                  AND deleted_at IS NULL
                  AND LOWER(COALESCE(status, 'active')) NOT IN ('deleted', 'archived', 'inactive', 'discontinued')
                GROUP BY product_id
            ) vp ON vp.product_id = p.id
            WHERE pa.product_id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": product_ids},
    )
    return [dict(row._mapping) for row in result]


async def list_accessory_product_meta_rows(session: AsyncSession, accessory_ids: list[UUID]) -> list[dict]:
    if not accessory_ids:
        return []
    result = await session.execute(
        text(
            """
            SELECT
                p.id::text AS accessory_id,
                p.sku,
                p.name,
                p.image_url AS image_url,
                p.image_url AS "imageUrl",
                COALESCE(NULLIF(p.price, 0), vp.min_price, 0) AS price,
                COALESCE(NULLIF(p.sale_price, 0), vp.min_sale_price) AS "discountPrice",
                COALESCE(NULLIF(p.sale_price, 0), vp.min_sale_price) AS "salePrice",
                GREATEST(COALESCE(vs.variant_stock, 0), COALESCE(p.stock_quantity, 0)) AS stock_quantity,
                GREATEST(COALESCE(vs.variant_stock, 0), COALESCE(p.stock_quantity, 0)) AS "stockQuantity",
                p.status
            FROM products p
            LEFT JOIN (
                SELECT product_id, SUM(stock_quantity) AS variant_stock
                FROM product_variants
                WHERE is_active = TRUE
                  AND deleted_at IS NULL
                  AND LOWER(COALESCE(status, 'active')) NOT IN ('deleted', 'archived', 'inactive', 'discontinued')
                GROUP BY product_id
            ) vs ON vs.product_id = p.id
            LEFT JOIN (
                SELECT product_id,
                       MIN(NULLIF(price, 0)) AS min_price,
                       MIN(COALESCE(NULLIF(sale_price, 0), NULLIF(price, 0))) AS min_sale_price
                FROM product_variants
                WHERE is_active = TRUE
                  AND deleted_at IS NULL
                  AND LOWER(COALESCE(status, 'active')) NOT IN ('deleted', 'archived', 'inactive', 'discontinued')
                GROUP BY product_id
            ) vp ON vp.product_id = p.id
            WHERE p.id IN :ids
              AND p.deleted_at IS NULL
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": accessory_ids},
    )
    return [dict(row._mapping) for row in result]


async def list_product_attached_service_rows(session: AsyncSession, product_ids: list[UUID]) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT pas.product_id::text AS product_id, s.id::text AS service_id, s.code, s.name,
                   s.service_type, s.attribute_group, s.duration_months, s.price_mode,
                   s.fixed_price, s.percent_value, s.base_amount, s.metadata,
                   pas.override_price
            FROM product_attached_services pas
            JOIN attached_services s ON s.id = pas.service_id
            WHERE pas.product_id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": product_ids},
    )
    return [dict(row._mapping) for row in result]
