"""Category repository helpers split by subdomain."""

import json
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_category_by_id(session: AsyncSession, category_id: UUID) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT *
            FROM categories
            WHERE id = :category_id
              AND COALESCE(is_deleted, FALSE) = FALSE
            """
        ),
        {"category_id": category_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def category_descendant_contains(session: AsyncSession, *, category_id: UUID, parent_id: UUID) -> bool:
    row = (
        await session.execute(
            text(
                """
                WITH RECURSIVE descendants AS (
                    SELECT id
                    FROM categories
                    WHERE parent_id = :category_id
                      AND COALESCE(is_deleted, FALSE) = FALSE
                    UNION ALL
                    SELECT child.id
                    FROM categories child
                    JOIN descendants d ON child.parent_id = d.id
                    WHERE COALESCE(child.is_deleted, FALSE) = FALSE
                )
                SELECT 1
                FROM descendants
                WHERE id = :parent_id
                LIMIT 1
                """
            ),
            {"category_id": category_id, "parent_id": parent_id},
        )
    ).first()
    return bool(row)


async def get_category_path_depth(session: AsyncSession, category_id: UUID) -> int:
    result = await session.execute(
        text("SELECT COALESCE(nlevel(path), 1) FROM categories WHERE id = :parent_id AND COALESCE(is_deleted, FALSE) = FALSE"),
        {"parent_id": category_id},
    )
    return int(result.scalar() or 0)


async def get_category_subtree_depth(session: AsyncSession, category_id: UUID) -> int:
    result = await session.execute(
        text(
            """
            SELECT COALESCE(MAX(nlevel(child.path) - nlevel(parent.path) + 1), 1)
            FROM categories parent
            LEFT JOIN categories child ON child.path <@ parent.path
            WHERE parent.id = :category_id
              AND COALESCE(child.is_deleted, FALSE) = FALSE
            """
        ),
        {"category_id": category_id},
    )
    return int(result.scalar() or 1)


async def list_ancestor_spec_fields(session: AsyncSession, *, parent_id: UUID, category_id: UUID | None) -> list[list[dict]]:
    rows = (
        await session.execute(
            text(
                """
                WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id, spec_fields
                    FROM categories
                    WHERE id = :parent_id
                      AND COALESCE(is_deleted, FALSE) = FALSE
                    UNION ALL
                    SELECT parent.id, parent.parent_id, parent.spec_fields
                    FROM categories parent
                    JOIN ancestors child ON child.parent_id = parent.id
                    WHERE COALESCE(parent.is_deleted, FALSE) = FALSE
                )
                SELECT spec_fields
                FROM ancestors
                WHERE (CAST(:category_id AS UUID) IS NULL OR id <> CAST(:category_id AS UUID))
                """
            ),
            {"parent_id": parent_id, "category_id": category_id},
        )
    ).mappings().all()
    return [row["spec_fields"] for row in rows]


async def count_products_using_spec_keys(session: AsyncSession, *, category_id: UUID, keys: list[str]) -> int:
    result = await session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM products p
            WHERE (p.category_id = :category_id OR p.subcategory_id = :category_id)
              AND p.specifications ?| CAST(:keys AS text[])
            """
        ),
        {"category_id": category_id, "keys": keys},
    )
    return int(result.scalar() or 0)


async def find_running_migration_for_category_branch(session: AsyncSession, ids: list[UUID]) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                WITH target AS (
                    SELECT id, path
                    FROM categories
                    WHERE id IN :ids
                      AND COALESCE(is_deleted, FALSE) = FALSE
                ),
                running AS (
                    SELECT jobs.id, jobs.category_id, jobs.status, c.path
                    FROM category_migration_jobs jobs
                    JOIN categories c ON c.id = jobs.category_id
                    WHERE jobs.status IN ('PENDING', 'RUNNING', 'IN_PROGRESS')
                )
                SELECT running.category_id::text AS category_id, running.id::text AS job_id, running.status
                FROM running
                JOIN target ON running.path @> target.path OR target.path @> running.path
                LIMIT 1
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": ids},
        )
    ).mappings().first()
    return dict(row) if row else None


async def list_stale_category_migration_jobs(session: AsyncSession, *, stale_after_minutes: int) -> list[dict]:
    rows = (
        await session.execute(
            text(
                """
                SELECT jobs.id, jobs.category_id
                FROM category_migration_jobs jobs
                WHERE jobs.status IN ('PENDING', 'RUNNING', 'IN_PROGRESS')
                  AND jobs.updated_at < NOW() - make_interval(mins => :stale_after_minutes)
                """
            ),
            {"stale_after_minutes": stale_after_minutes},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def mark_category_migration_failed(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE category_migration_jobs
            SET status = 'FAILED',
                error_message = COALESCE(error_message, 'Migration watchdog released stale job after timeout.'),
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": job_id},
    )


async def unlock_category_workflow_status(session: AsyncSession, category_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE categories
            SET workflow_status = CASE
                WHEN status = 'ACTIVE' THEN 'APPROVED'
                WHEN status = 'INACTIVE' THEN 'APPROVED'
                ELSE status
            END,
            updated_at = NOW()
            WHERE id = :category_id
            """
        ),
        {"category_id": category_id},
    )


async def list_root_ids_for_categories(session: AsyncSession, ids: list[UUID]) -> list[dict]:
    rows = (
        await session.execute(
            text(
                """
                SELECT id, path::text AS path
                FROM categories
                WHERE id IN :ids
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": ids},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def list_visible_root_category_ids(session: AsyncSession) -> list[UUID]:
    return list(
        (
            await session.execute(
                text(
                    """
                    SELECT id
                    FROM categories
                    WHERE parent_id IS NULL
                      AND is_active = TRUE
                      AND status = 'ACTIVE'
                      AND COALESCE(is_deleted, FALSE) = FALSE
                    ORDER BY sort_order, name
                    """
                )
            )
        ).scalars().all()
    )


async def fetch_visible_category_branch(session: AsyncSession, root_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    c.id::text,
                    c.parent_id::text AS "parentId",
                    c.code,
                    c.slug,
                    c.name,
                    c.icon,
                    c.icon_url AS "iconUrl",
                    c.banner_url AS "bannerUrl",
                    COALESCE(c.spec_fields, '[]'::jsonb) AS "specFields",
                    c.filter_config AS "filterConfig",
                    c.sort_order AS "order",
                    COALESCE(
                        jsonb_agg(
                            DISTINCT jsonb_build_object(
                                'id', child.id::text,
                                'code', child.code,
                                'slug', child.slug,
                                'name', child.name,
                                'sortOrder', child.sort_order
                            )
                        ) FILTER (
                            WHERE child.id IS NOT NULL
                              AND COALESCE(child.is_deleted, FALSE) = FALSE
                              AND child.status = 'ACTIVE'
                        ),
                        '[]'::jsonb
                    ) AS children
                FROM categories c
                LEFT JOIN categories child ON child.parent_id = c.id
                WHERE c.id = :root_id
                  AND c.parent_id IS NULL
                  AND c.is_active = TRUE
                  AND c.status = 'ACTIVE'
                  AND COALESCE(c.is_deleted, FALSE) = FALSE
                GROUP BY c.id
                """
            ),
            {"root_id": root_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def list_visible_product_ids_in_category_branch(session: AsyncSession, category_id: UUID) -> list[UUID]:
    result = await session.execute(
        text(
            """
            WITH branch AS (
                SELECT path
                FROM categories
                WHERE id = :category_id
            )
            SELECT DISTINCT p.id
            FROM products p
            JOIN categories c ON c.id = COALESCE(p.subcategory_id, p.category_id)
            JOIN branch b ON c.path <@ b.path
            WHERE p.status = 'ACTIVE'
            """
        ),
        {"category_id": category_id},
    )
    return list(result.scalars().all())


async def hide_products_by_category(session: AsyncSession, product_ids: list[UUID]) -> None:
    await session.execute(
        text(
            """
            UPDATE products
            SET status = 'INACTIVE',
                hidden_by_category = TRUE,
                updated_at = NOW()
            WHERE id IN :ids
              AND status = 'ACTIVE'
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": product_ids},
    )
    await session.execute(
        text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id IN :ids").bindparams(bindparam("ids", expanding=True)),
        {"ids": product_ids},
    )


async def restore_products_hidden_by_category(session: AsyncSession, category_id: UUID) -> int:
    result = await session.execute(
        text(
            """
            WITH branch AS (
                SELECT path
                FROM categories
                WHERE id = :category_id
            ),
            restored AS (
                UPDATE products p
                SET status = 'ACTIVE',
                    hidden_by_category = FALSE,
                    updated_at = NOW()
                FROM categories c, branch branch_row
                WHERE c.id = COALESCE(p.subcategory_id, p.category_id)
                  AND c.path <@ branch_row.path
                  AND p.hidden_by_category = TRUE
                  AND p.hidden_by_brand = FALSE
                  AND p.status = 'INACTIVE'
                  AND c.status = 'ACTIVE'
                  AND c.is_active = TRUE
                  AND COALESCE(c.is_deleted, FALSE) = FALSE
                  AND NOT EXISTS (
                    SELECT 1
                    FROM brands b
                    WHERE b.id = p.brand_id
                      AND b.is_active = FALSE
                  )
                RETURNING p.id
            )
            SELECT id FROM restored
            """
        ),
        {"category_id": category_id},
    )
    product_ids = list(result.scalars().all())
    if product_ids:
        await session.execute(
            text(
                """
                UPDATE product_variants
                SET is_active = TRUE,
                    updated_at = NOW()
                WHERE product_id IN :ids
                  AND deleted_at IS NULL
                  AND status NOT IN ('deleted', 'archived')
                """
            ).bindparams(bindparam("ids", expanding=True)),
            {"ids": product_ids},
        )
    return len(product_ids)
