import json
from uuid import UUID, uuid4

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def mark_status_job_processing(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(text("UPDATE brand_status_jobs SET status = 'PROCESSING', updated_at = NOW() WHERE id = :id"), {"id": job_id})


async def count_brand_products(session: AsyncSession, brand_id: UUID) -> int:
    return int((await session.execute(text("SELECT COUNT(*) FROM products WHERE brand_id = :brand_id"), {"brand_id": brand_id})).scalar_one())


async def update_status_job_total(session: AsyncSession, *, job_id: UUID, total: int) -> None:
    await session.execute(text("UPDATE brand_status_jobs SET total_products = :total WHERE id = :id"), {"id": job_id, "total": total})


async def list_active_product_ids_by_brand(session: AsyncSession, brand_id: UUID) -> list[UUID]:
    return list((await session.execute(text("SELECT id FROM products WHERE brand_id = :brand_id AND status = 'ACTIVE'"), {"brand_id": brand_id})).scalars().all())


async def hide_products_by_brand(session: AsyncSession, product_ids: list[UUID]) -> None:
    await session.execute(
        text(
            """
            UPDATE products
            SET status = 'INACTIVE',
                hidden_by_brand = TRUE,
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


async def restore_products_hidden_by_brand(session: AsyncSession, brand_id: UUID) -> int:
    result = await session.execute(
        text(
            """
            WITH restored AS (
                UPDATE products p
                SET status = 'ACTIVE',
                    hidden_by_brand = FALSE,
                    updated_at = NOW()
                FROM brands b
                WHERE b.id = :brand_id
                  AND p.brand_id = b.id
                  AND p.hidden_by_brand = TRUE
                  AND p.hidden_by_category = FALSE
                  AND p.status = 'INACTIVE'
                  AND b.is_active = TRUE
                  AND NOT EXISTS (
                    SELECT 1
                    FROM categories c
                    WHERE c.id = COALESCE(p.subcategory_id, p.category_id)
                      AND (
                        c.status <> 'ACTIVE'
                        OR c.is_active = FALSE
                        OR COALESCE(c.is_deleted, FALSE) = TRUE
                      )
                  )
                RETURNING p.id
            )
            SELECT id FROM restored
            """
        ),
        {"brand_id": brand_id},
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


async def increment_status_job_processed(session: AsyncSession, *, job_id: UUID, count: int) -> None:
    await session.execute(
        text("UPDATE brand_status_jobs SET processed_products = processed_products + :count, updated_at = NOW() WHERE id = :id"),
        {"id": job_id, "count": count},
    )


async def mark_status_job_completed(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(text("UPDATE brand_status_jobs SET status = 'COMPLETED', processed_products = total_products, updated_at = NOW() WHERE id = :id"), {"id": job_id})


async def mark_status_job_failed(session: AsyncSession, *, job_id: UUID, error: str) -> None:
    await session.execute(
        text("UPDATE brand_status_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
        {"id": job_id, "error": error[:1000]},
    )


async def count_existing_categories(session: AsyncSession, category_ids: list[UUID]) -> int:
    return int(
        (
            await session.execute(
                text("SELECT COUNT(*) FROM categories WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
                {"ids": category_ids},
            )
        ).scalar_one()
    )


async def delete_brand_categories(session: AsyncSession, brand_id: UUID) -> None:
    await session.execute(text("DELETE FROM brand_categories WHERE brand_id = :brand_id"), {"brand_id": brand_id})


async def insert_brand_category(session: AsyncSession, *, brand_id: UUID, category_id: UUID) -> None:
    await session.execute(
        text("INSERT INTO brand_categories (brand_id, category_id) VALUES (:brand_id, :category_id) ON CONFLICT DO NOTHING"),
        {"brand_id": brand_id, "category_id": category_id},
    )


async def brand_code_exists(session: AsyncSession, *, code: str, exclude_id: UUID | None = None) -> bool:
    row = (
        await session.execute(
            text(
                """
                SELECT id
                FROM brands
                WHERE lower(code) = lower(:code)
                  AND id != COALESCE(:exclude_id, '00000000-0000-0000-0000-000000000000'::uuid)
                """
            ),
            {"code": code.strip(), "exclude_id": exclude_id},
        )
    ).first()
    return bool(row)


async def brand_slug_exists(session: AsyncSession, *, slug: str, exclude_id: UUID | None = None) -> bool:
    row = (
        await session.execute(
            text(
                """
                SELECT id
                FROM brands
                WHERE lower(slug) = lower(:slug)
                  AND id != COALESCE(:exclude_id, '00000000-0000-0000-0000-000000000000'::uuid)
                """
            ),
            {"slug": slug.strip(), "exclude_id": exclude_id},
        )
    ).first()
    return bool(row)


async def get_redirect_new_slug(session: AsyncSession, slug: str) -> str | None:
    return (
        await session.execute(
            text("SELECT new_slug FROM brand_slug_redirects WHERE old_slug = :slug"),
            {"slug": slug},
        )
    ).scalar_one_or_none()


async def delete_brand_redirect_conflicts(session: AsyncSession, *, brand_id: UUID, old_slug: str, new_slug: str) -> None:
    await session.execute(
        text("DELETE FROM brand_slug_redirects WHERE brand_id = :brand_id OR old_slug = :new_slug OR new_slug = :old_slug"),
        {"brand_id": brand_id, "new_slug": new_slug, "old_slug": old_slug},
    )


async def upsert_brand_redirect(session: AsyncSession, *, brand_id: UUID, old_slug: str, new_slug: str) -> None:
    await session.execute(
        text(
            """
            INSERT INTO brand_slug_redirects (id, brand_id, old_slug, new_slug)
            VALUES (:id, :brand_id, :old_slug, :new_slug)
            ON CONFLICT (old_slug) DO UPDATE
            SET brand_id = EXCLUDED.brand_id, new_slug = EXCLUDED.new_slug, created_at = NOW()
            """
        ),
        {"id": uuid4(), "brand_id": brand_id, "old_slug": old_slug, "new_slug": new_slug},
    )


async def list_admin_brands(session: AsyncSession, *, page: int, limit: int, search: str | None, status_filter: str) -> dict:
    where_clauses = []
    params: dict = {"limit": limit, "offset": (page - 1) * limit}
    if search:
        where_clauses.append("(b.name ILIKE :search OR b.code ILIKE :search OR b.slug ILIKE :search)")
        params["search"] = f"%{search.strip()}%"
    if status_filter == "active":
        where_clauses.append("b.is_active = TRUE")
    elif status_filter == "inactive":
        where_clauses.append("b.is_active = FALSE")
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    total = (await session.execute(text(f"SELECT COUNT(*) FROM brands b {where_sql}"), params)).scalar_one()
    result = await session.execute(
        text(
            f"""
            SELECT
                b.id::text,
                b.code,
                b.slug,
                b.name,
                b.logo_url AS "logoUrl",
                b.logo_alt_text AS "logoAltText",
                b.landing_title AS "landingTitle",
                b.sort_order AS "order",
                b.is_active AS "isActive",
                b.updated_at AS "updatedAt",
                COUNT(DISTINCT p.id) AS "productCount",
                COALESCE(
                    jsonb_agg(DISTINCT c.id::text) FILTER (WHERE c.id IS NOT NULL),
                    '[]'::jsonb
                ) AS "categoryIds"
            FROM brands b
            LEFT JOIN brand_categories bc ON bc.brand_id = b.id
            LEFT JOIN categories c ON c.id = bc.category_id
            LEFT JOIN products p ON p.brand_id = b.id OR p.brand = b.name
            {where_sql}
            GROUP BY b.id
            ORDER BY b.sort_order, b.name
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    return {"items": [dict(row._mapping) for row in result], "page": page, "limit": limit, "total": total}


async def is_brand_code_available(session: AsyncSession, *, code: str, exclude_id: UUID | None) -> bool:
    params: dict = {"code": code.strip()}
    exclude_clause = ""
    if exclude_id is not None:
        exclude_clause = "AND id != :exclude_id"
        params["exclude_id"] = exclude_id
    row = (
        await session.execute(
            text(
                f"""
                SELECT 1
                FROM brands
                WHERE lower(code) = lower(:code)
                  {exclude_clause}
                """
            ),
            params,
        )
    ).first()
    return row is None


async def insert_brand(session: AsyncSession, *, brand_id: UUID, code: str, slug: str, name: str, logo_url: str | None, logo_alt_text: str | None, landing_title: str | None, sort_order: int, is_active: bool) -> None:
    await session.execute(
        text(
            """
            INSERT INTO brands (
                id, code, slug, name, logo_url, logo_alt_text, landing_title, sort_order, is_active
            )
            VALUES (
                :id, :code, :slug, :name, :logo_url, :logo_alt_text, :landing_title, :sort_order, :is_active
            )
            """
        ),
        {
            "id": brand_id,
            "code": code,
            "slug": slug,
            "name": name,
            "logo_url": logo_url,
            "logo_alt_text": logo_alt_text,
            "landing_title": landing_title,
            "sort_order": sort_order,
            "is_active": is_active,
        },
    )


async def get_brand_slug(session: AsyncSession, brand_id: UUID) -> dict | None:
    row = (await session.execute(text("""
        SELECT slug, is_active
        FROM brands WHERE id = :id
    """), {"id": brand_id})).mappings().first()
    return dict(row) if row else None


async def update_brand(session: AsyncSession, *, brand_id: UUID, code: str, slug: str, name: str, logo_url: str | None, logo_alt_text: str | None, landing_title: str | None, sort_order: int, is_active: bool) -> None:
    await session.execute(
        text(
            """
            UPDATE brands
                SET code = :code, slug = :slug, name = :name, logo_url = :logo_url, logo_alt_text = :logo_alt_text,
                landing_title = :landing_title,
                sort_order = :sort_order, is_active = :is_active, updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": brand_id,
            "code": code,
            "slug": slug,
            "name": name,
            "logo_url": logo_url,
            "logo_alt_text": logo_alt_text,
            "landing_title": landing_title,
            "sort_order": sort_order,
            "is_active": is_active,
        },
    )


async def list_brand_import_jobs(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                mode,
                source_filename AS "sourceFilename",
                total_rows AS "totalRows",
                imported_rows AS "importedRows",
                updated_rows AS "updatedRows",
                skipped_rows AS "skippedRows",
                status,
                progress,
                processed_rows AS "processedRows",
                error_message AS "errorMessage",
                report,
                started_at AS "startedAt",
                completed_at AS "completedAt",
                created_at AS "createdAt"
            FROM brand_import_jobs
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def get_brand_import_job(session: AsyncSession, job_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT
                    id::text,
                    mode,
                    source_filename AS "sourceFilename",
                    total_rows AS "totalRows",
                    processed_rows AS "processedRows",
                    imported_rows AS "importedRows",
                    updated_rows AS "updatedRows",
                    skipped_rows AS "skippedRows",
                    status,
                    progress,
                    error_message AS "errorMessage",
                    report,
                    started_at AS "startedAt",
                    completed_at AS "completedAt",
                    created_at AS "createdAt"
                FROM brand_import_jobs
                WHERE id = :id
                """
            ),
            {"id": job_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_brand_status(session: AsyncSession, *, brand_id: UUID, is_active: bool) -> int:
    result = await session.execute(
        text("UPDATE brands SET is_active = :is_active, updated_at = NOW() WHERE id = :id"),
        {"id": brand_id, "is_active": is_active},
    )
    return int(result.rowcount or 0)


async def create_brand_status_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    brand_id: UUID,
    target_is_active: bool = False,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO brand_status_jobs (id, brand_id, target_is_active, status)
            VALUES (:id, :brand_id, :target_is_active, 'PENDING')
            """
        ),
        {"id": job_id, "brand_id": brand_id, "target_is_active": target_is_active},
    )


async def list_brands_by_ids(session: AsyncSession, brand_ids: list[UUID]) -> list[dict]:
    rows = (
        await session.execute(
            text("SELECT id, slug FROM brands WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": brand_ids},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


async def update_brands_status(session: AsyncSession, *, brand_ids: list[UUID], is_active: bool) -> None:
    await session.execute(
        text("UPDATE brands SET is_active = :is_active, updated_at = NOW() WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
        {"ids": brand_ids, "is_active": is_active},
    )


async def list_brand_status_jobs(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, brand_id::text AS "brandId", target_is_active AS "targetIsActive",
                   status, total_products AS "totalProducts", processed_products AS "processedProducts",
                   error_message AS "errorMessage", created_at AS "createdAt", updated_at AS "updatedAt"
            FROM brand_status_jobs
            ORDER BY created_at DESC
            LIMIT 20
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def get_brand_for_delete(session: AsyncSession, brand_id: UUID) -> dict | None:
    row = (
        await session.execute(text("SELECT id::text, code, slug, name FROM brands WHERE id = :id"), {"id": brand_id})
    ).mappings().first()
    return dict(row) if row else None


async def count_products_for_brand_delete(session: AsyncSession, brand_id: UUID) -> int:
    return int(
        (
            await session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM products p
                    JOIN brands b ON b.id = :id
                    WHERE p.brand_id = :id OR p.brand = b.name
                    """
                ),
                {"id": brand_id},
            )
        ).scalar_one()
    )


async def delete_brand(session: AsyncSession, brand_id: UUID) -> int:
    result = await session.execute(text("DELETE FROM brands WHERE id = :id"), {"id": brand_id})
    return int(result.rowcount or 0)


async def audit_brand_hard_deleted(session: AsyncSession, *, user_id: UUID, brand: dict) -> None:
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs (user_id, event_type, metadata)
            VALUES (:user_id, 'BRAND_HARD_DELETED', CAST(:metadata AS jsonb))
            """
        ),
        {"user_id": user_id, "metadata": json.dumps({"brand": brand}, ensure_ascii=False)},
    )


async def bump_brand_cache_versions(session: AsyncSession, slugs: list[str]) -> None:
    if not slugs:
        return
    await session.execute(
        text("UPDATE brands SET cache_version = cache_version + 1 WHERE slug IN :slugs").bindparams(bindparam("slugs", expanding=True)),
        {"slugs": slugs},
    )


async def audit_brand_event(
    session: AsyncSession,
    *,
    event_type: str,
    metadata: dict,
    user_id: UUID | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs (user_id, event_type, metadata)
            VALUES (:user_id, :event_type, CAST(:metadata AS jsonb))
            """
        ),
        {"user_id": user_id, "event_type": event_type, "metadata": json.dumps(metadata, ensure_ascii=False, default=str)},
    )


async def create_brand_import_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    items: list[dict],
    source_path: str | None,
    total_rows: int,
    mode: str,
    source_filename: str | None,
    user_id: UUID | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO brand_import_jobs (
                id, mode, source_filename, total_rows, imported_rows, updated_rows, skipped_rows,
                status, progress, processed_rows, report, payload, source_path
            )
            VALUES (
                :id, :mode, :source_filename, :total_rows, 0, 0, 0,
                'QUEUED', 0, 0, '[]'::jsonb, CAST(:payload AS jsonb), :source_path
            )
            """
        ),
        {
            "id": job_id,
            "mode": mode,
            "source_filename": source_filename,
            "total_rows": total_rows,
            "payload": json.dumps({"items": items, "requestedBy": str(user_id) if user_id else None}, ensure_ascii=False),
            "source_path": source_path,
        },
    )


async def get_brand_import_job_for_update(session: AsyncSession, job_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, mode, source_filename, source_path, total_rows, payload, status
                FROM brand_import_jobs
                WHERE id = :id
                FOR UPDATE
                """
            ),
            {"id": job_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def mark_brand_import_job_processing(session: AsyncSession, job_id: UUID) -> None:
    await session.execute(
        text("UPDATE brand_import_jobs SET status = 'PROCESSING', started_at = NOW(), error_message = NULL WHERE id = :id"),
        {"id": job_id},
    )


async def get_brand_by_code(session: AsyncSession, code: str) -> dict | None:
    row = (
        await session.execute(
            text("SELECT id, slug FROM brands WHERE lower(code) = lower(:code)"),
            {"code": code},
        )
    ).mappings().first()
    return dict(row) if row else None


async def upsert_brand_from_import(
    session: AsyncSession,
    *,
    brand_id: UUID,
    code: str,
    slug: str,
    name: str,
    logo_url: str | None,
    sort_order: int,
    mode: str,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                INSERT INTO brands (id, code, slug, name, logo_url, sort_order, is_active)
                VALUES (:id, :code, :slug, :name, :logo_url, :sort_order, TRUE)
                ON CONFLICT (code) DO UPDATE
                SET name = EXCLUDED.name,
                    logo_url = COALESCE(EXCLUDED.logo_url, brands.logo_url),
                    sort_order = EXCLUDED.sort_order,
                    cache_version = brands.cache_version + 1,
                    updated_at = NOW()
                WHERE :mode = 'upsert'
                RETURNING (xmax = 0) AS inserted, slug
                """
            ),
            {
                "id": brand_id,
                "code": code,
                "slug": slug,
                "name": name,
                "logo_url": logo_url,
                "sort_order": sort_order,
                "mode": mode,
            },
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_brand_import_job_progress(
    session: AsyncSession,
    *,
    job_id: UUID,
    processed_rows: int,
    progress: int,
    imported_rows: int,
    updated_rows: int,
    skipped_rows: int,
    report: list[dict],
) -> None:
    await session.execute(
        text(
            """
            UPDATE brand_import_jobs
            SET processed_rows = :processed_rows, progress = :progress,
                imported_rows = :imported_rows, updated_rows = :updated_rows,
                skipped_rows = :skipped_rows, report = CAST(:report AS jsonb)
            WHERE id = :id
            """
        ),
        {
            "id": job_id,
            "processed_rows": processed_rows,
            "progress": progress,
            "imported_rows": imported_rows,
            "updated_rows": updated_rows,
            "skipped_rows": skipped_rows,
            "report": json.dumps(report, ensure_ascii=False),
        },
    )


async def mark_brand_import_job_completed(
    session: AsyncSession,
    *,
    job_id: UUID,
    imported_rows: int,
    updated_rows: int,
    skipped_rows: int,
    report: list[dict],
) -> None:
    await session.execute(
        text(
            """
            UPDATE brand_import_jobs
            SET status = 'COMPLETED', progress = 100, completed_at = NOW(),
                imported_rows = :imported_rows, updated_rows = :updated_rows,
                skipped_rows = :skipped_rows, report = CAST(:report AS jsonb)
            WHERE id = :id
            """
        ),
        {
            "id": job_id,
            "imported_rows": imported_rows,
            "updated_rows": updated_rows,
            "skipped_rows": skipped_rows,
            "report": json.dumps(report, ensure_ascii=False),
        },
    )


async def mark_brand_import_job_failed(session: AsyncSession, *, job_id: UUID, error_message: str) -> None:
    await session.execute(
        text(
            """
            UPDATE brand_import_jobs
            SET status = 'FAILED', error_message = :error_message, completed_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": job_id, "error_message": error_message},
    )
