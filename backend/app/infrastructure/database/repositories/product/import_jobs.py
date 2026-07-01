import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def mark_product_import_processing(session: AsyncSession, *, job_id: UUID, total: int) -> None:
    await session.execute(
        text("UPDATE product_import_jobs SET status = 'PROCESSING', total_rows = :total, updated_at = NOW() WHERE id = :id"),
        {"id": job_id, "total": total},
    )


async def insert_imported_product(
    session: AsyncSession,
    *,
    product_id: UUID,
    sku: str,
    name: str,
    slug: str,
    category: str,
    brand: str,
    description: str,
    seo_metadata: dict,
    sales_config: dict,
    price: float,
    sale_price: float | None,
    image_url: str | None,
    status: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO products (
                id, sku, name, slug, category, brand, description, specifications,
                seo_metadata, sales_config, price, sale_price, stock_quantity,
                image_url, images, colors, capacities, promotions, status
            )
            VALUES (
                :id, :sku, :name, :slug, :category, :brand, :description, '{}'::jsonb,
                CAST(:seo_metadata AS jsonb), CAST(:sales_config AS jsonb), :price,
                :sale_price, 0, :image_url, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb,
                '[]'::jsonb, :status
            )
            """
        ),
        {
            "id": product_id,
            "sku": sku,
            "name": name,
            "slug": slug,
            "category": category,
            "brand": brand,
            "description": description,
            "seo_metadata": json.dumps(seo_metadata),
            "sales_config": json.dumps(sales_config),
            "price": price,
            "sale_price": sale_price,
            "image_url": image_url,
            "status": status,
        },
    )


async def update_product_import_progress(session: AsyncSession, *, job_id: UUID, imported: int, failed: int) -> None:
    await session.execute(
        text(
            """
            UPDATE product_import_jobs
            SET processed_rows = processed_rows + 1,
                imported_rows = :imported,
                failed_rows = :failed,
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": job_id, "imported": imported, "failed": failed},
    )


async def mark_product_import_completed(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text("UPDATE product_import_jobs SET status = 'COMPLETED', updated_at = NOW() WHERE id = :id"),
        {"id": job_id},
    )


async def mark_product_import_failed(session: AsyncSession, *, job_id: UUID, error: str) -> None:
    await session.execute(
        text("UPDATE product_import_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
        {"id": job_id, "error": error[:1000]},
    )
