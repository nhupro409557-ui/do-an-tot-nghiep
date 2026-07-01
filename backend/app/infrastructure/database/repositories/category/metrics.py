"""Category repository helpers split by subdomain."""

import json
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def insert_category_migration_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    category_id: UUID,
    old_parent_id: UUID | None,
    new_parent_id: UUID | None,
    total_products: int,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO category_migration_jobs (id, category_id, old_parent_id, new_parent_id, total_products)
            VALUES (:id, :category_id, :old_parent_id, :new_parent_id, :total_products)
            """
        ),
        {
            "id": job_id,
            "category_id": category_id,
            "old_parent_id": old_parent_id,
            "new_parent_id": new_parent_id,
            "total_products": total_products,
        },
    )


async def mark_category_workflow_migrating(session: AsyncSession, category_id: UUID) -> None:
    await session.execute(
        text("UPDATE categories SET workflow_status = 'MIGRATING', updated_at = NOW() WHERE id = :id"),
        {"id": category_id},
    )


async def list_category_audit_logs(session: AsyncSession, category_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                category_id::text AS "categoryId",
                actor_id::text AS "actorId",
                action_type AS "actionType",
                old_value AS "oldValue",
                new_value AS "newValue",
                created_at AS "createdAt"
            FROM category_audit_logs
            WHERE category_id = :category_id
            ORDER BY created_at DESC
            LIMIT 100
            """
        ),
        {"category_id": category_id},
    )
    return [dict(row._mapping) for row in result]


async def list_category_migration_jobs(session: AsyncSession, category_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                category_id::text AS "categoryId",
                old_parent_id::text AS "oldParentId",
                new_parent_id::text AS "newParentId",
                status,
                total_products AS "totalProducts",
                processed_products AS "processedProducts",
                error_message AS "errorMessage",
                created_at AS "createdAt",
                updated_at AS "updatedAt",
                completed_at AS "completedAt"
            FROM category_migration_jobs
            WHERE category_id = :category_id
            ORDER BY created_at DESC
            LIMIT 50
            """
        ),
        {"category_id": category_id},
    )
    return [dict(row._mapping) for row in result]


async def get_category_migration_job_metrics(session: AsyncSession, *, stale_after_minutes: int) -> dict:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'FAILED') AS failed_jobs,
                    COUNT(*) FILTER (WHERE status IN ('PENDING', 'RUNNING', 'IN_PROGRESS')) AS running_jobs,
                    COUNT(*) FILTER (
                        WHERE status IN ('PENDING', 'RUNNING', 'IN_PROGRESS')
                          AND updated_at < NOW() - make_interval(mins => :stale_after_minutes)
                    ) AS stale_jobs,
                    COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) FILTER (WHERE completed_at IS NOT NULL), 0) AS avg_duration_seconds
                FROM category_migration_jobs
                """
            ),
            {"stale_after_minutes": stale_after_minutes},
        )
    ).mappings().one()
    return dict(row)


async def get_category_business_metrics(session: AsyncSession) -> dict:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE c.status IN ('ACTIVE', 'APPROVED') AND COALESCE(c.is_deleted, FALSE) = FALSE) AS active_categories,
                    COUNT(*) FILTER (
                        WHERE c.status IN ('ACTIVE', 'APPROVED')
                          AND COALESCE(c.is_deleted, FALSE) = FALSE
                          AND COALESCE(product_counts.product_count, 0) = 0
                    ) AS empty_active_categories,
                    COALESCE(AVG(product_counts.product_count) FILTER (
                        WHERE c.status IN ('ACTIVE', 'APPROVED') AND COALESCE(c.is_deleted, FALSE) = FALSE
                    ), 0) AS avg_products_per_active_category
                FROM categories c
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) AS product_count
                    FROM products p
                    WHERE p.category_id = c.id OR p.subcategory_id = c.id
                ) product_counts ON TRUE
                """
            )
        )
    ).mappings().one()
    return dict(row)
