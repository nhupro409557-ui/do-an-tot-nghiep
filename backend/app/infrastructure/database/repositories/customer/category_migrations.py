from .common import *

async def mark_category_migration_running(session: AsyncSession, *, job_id: UUID, category_id: UUID) -> None:
    await session.execute(text("UPDATE category_migration_jobs SET status = 'RUNNING', updated_at = NOW() WHERE id = :id"), {"id": job_id})
    await session.execute(text("UPDATE categories SET workflow_status = 'MIGRATING', updated_at = NOW() WHERE id = :category_id"), {"category_id": category_id})


async def list_category_migration_allowed_fields(session: AsyncSession, category_id: UUID) -> list[dict]:
    fields = await session.scalar(
        text(
            """
            SELECT COALESCE(parent.spec_fields, '[]'::jsonb) || COALESCE(c.spec_fields, '[]'::jsonb) AS fields
            FROM categories c
            LEFT JOIN categories parent ON parent.id = c.parent_id
            WHERE c.id = :category_id
            """
        ),
        {"category_id": category_id},
    )
    return list(fields or [])


async def list_products_for_category_migration(session: AsyncSession, category_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id, specifications
            FROM products
            WHERE category_id = :category_id OR subcategory_id = :category_id
            """
        ),
        {"category_id": category_id},
    )
    return [dict(row._mapping) for row in result]


async def update_category_migration_total(session: AsyncSession, *, job_id: UUID, total: int) -> None:
    await session.execute(
        text("UPDATE category_migration_jobs SET total_products = :total, updated_at = NOW() WHERE id = :id"),
        {"id": job_id, "total": total},
    )


async def update_product_specifications(session: AsyncSession, *, product_id: UUID, specifications: dict) -> None:
    await session.execute(
        text("UPDATE products SET specifications = CAST(:specifications AS jsonb), updated_at = NOW() WHERE id = :id"),
        {"id": product_id, "specifications": json.dumps(specifications, ensure_ascii=False)},
    )


async def increment_category_migration_processed(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text("UPDATE category_migration_jobs SET processed_products = processed_products + 1, updated_at = NOW() WHERE id = :id"),
        {"id": job_id},
    )


async def complete_category_migration_job(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text("UPDATE category_migration_jobs SET status = 'COMPLETED', completed_at = NOW(), updated_at = NOW() WHERE id = :id"),
        {"id": job_id},
    )


async def fail_category_migration_job(session: AsyncSession, *, job_id: UUID, error: str) -> None:
    await session.execute(
        text("UPDATE category_migration_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
        {"id": job_id, "error": error[:1000]},
    )


async def reset_category_workflow_status(session: AsyncSession, category_id: UUID) -> None:
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
