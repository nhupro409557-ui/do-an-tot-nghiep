import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def create_product_import_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    source_filename: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO product_import_jobs (id, source_filename, status)
            VALUES (:id, :source_filename, 'PENDING')
            """
        ),
        {"id": job_id, "source_filename": source_filename},
    )


async def list_product_import_jobs(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, source_filename AS "sourceFilename", status, total_rows AS "totalRows",
                   processed_rows AS "processedRows", imported_rows AS "importedRows",
                   failed_rows AS "failedRows", error_message AS "errorMessage",
                   created_at AS "createdAt", updated_at AS "updatedAt"
            FROM product_import_jobs
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def create_product_export_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    filters: dict,
) -> None:
    await session.execute(
        text("INSERT INTO product_export_jobs (id, status, filters) VALUES (:id, 'PENDING', CAST(:filters AS jsonb))"),
        {"id": job_id, "filters": json.dumps(filters, ensure_ascii=False)},
    )


async def mark_product_export_processing(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text("UPDATE product_export_jobs SET status = 'PROCESSING', updated_at = NOW() WHERE id = :id"),
        {"id": job_id},
    )


async def list_products_for_export(session: AsyncSession, filters: dict) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, sku, name, brand, category, price, sale_price AS "discountPrice",
                   stock_quantity AS stock, status, seo_metadata, sales_config
            FROM products
            WHERE (:search = '' OR LOWER(name) LIKE LOWER(:pattern) OR LOWER(sku) LIKE LOWER(:pattern) OR LOWER(brand) LIKE LOWER(:pattern))
              AND (:status = '' OR status = :status)
            ORDER BY created_at DESC
            """
        ),
        {
            "search": filters.get("search", ""),
            "pattern": f"%{filters.get('search', '')}%",
            "status": filters.get("status", ""),
        },
    )
    return [dict(row._mapping) for row in result]


async def mark_product_export_completed(
    session: AsyncSession,
    *,
    job_id: UUID,
    total: int,
    file_path: str,
    download_url: str,
    expires_at: datetime,
) -> None:
    await session.execute(
        text(
            """
            UPDATE product_export_jobs
            SET status = 'COMPLETED', total_rows = :total, processed_rows = :total,
                file_path = :file_path, download_url = :download_url,
                expires_at = :expires_at, updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": job_id,
            "total": total,
            "file_path": file_path,
            "download_url": download_url,
            "expires_at": expires_at,
        },
    )


async def mark_product_export_failed(session: AsyncSession, *, job_id: UUID, error: str) -> None:
    await session.execute(
        text("UPDATE product_export_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
        {"id": job_id, "error": error[:1000]},
    )


async def list_product_export_jobs(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, status, filters, total_rows AS "totalRows", processed_rows AS "processedRows",
                   download_url AS "downloadUrl", expires_at AS "expiresAt", error_message AS "errorMessage",
                   created_at AS "createdAt", updated_at AS "updatedAt"
            FROM product_export_jobs
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
    )
    return [dict(row._mapping) for row in result]
