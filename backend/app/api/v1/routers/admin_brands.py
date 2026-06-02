import csv
import json
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user_id, require_permission
from app.api.v1.routers.admin_schemas import *
from app.api.v1.routers.admin_utils import ensure_not_data_url, slugify
from app.application.brands.import_jobs import audit_brand_event, bump_brand_cache_versions, enqueue_brand_import_job
from app.config import settings
from app.infrastructure.cache import get_redis
from app.infrastructure.database.session import AsyncSessionFactory, get_session


router = APIRouter()

async def process_brand_status_job(job_id: UUID, brand_id: UUID, target_is_active: bool) -> None:
    async with AsyncSessionFactory() as session:
        try:
            await session.execute(text("UPDATE brand_status_jobs SET status = 'PROCESSING', updated_at = NOW() WHERE id = :id"), {"id": job_id})
            total = (
                await session.execute(text("SELECT COUNT(*) FROM products WHERE brand_id = :brand_id"), {"brand_id": brand_id})
            ).scalar_one()
            await session.execute(text("UPDATE brand_status_jobs SET total_products = :total WHERE id = :id"), {"id": job_id, "total": total})
            if not target_is_active:
                product_rows = (
                    await session.execute(text("SELECT id FROM products WHERE brand_id = :brand_id AND status = 'ACTIVE'"), {"brand_id": brand_id})
                ).scalars().all()
                for index in range(0, len(product_rows), 100):
                    chunk = product_rows[index:index + 100]
                    if not chunk:
                        continue
                    await session.execute(
                        text("UPDATE products SET status = 'INACTIVE', updated_at = NOW() WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
                        {"ids": chunk},
                    )
                    await session.execute(
                        text("UPDATE product_variants SET is_active = FALSE, updated_at = NOW() WHERE product_id IN :ids").bindparams(bindparam("ids", expanding=True)),
                        {"ids": chunk},
                    )
                    await session.execute(
                        text("UPDATE brand_status_jobs SET processed_products = processed_products + :count, updated_at = NOW() WHERE id = :id"),
                        {"id": job_id, "count": len(chunk)},
                    )
                    await session.commit()
            await session.execute(text("UPDATE brand_status_jobs SET status = 'COMPLETED', processed_products = total_products, updated_at = NOW() WHERE id = :id"), {"id": job_id})
            await session.commit()
        except Exception as exc:
            await session.execute(
                text("UPDATE brand_status_jobs SET status = 'FAILED', error_message = :error, updated_at = NOW() WHERE id = :id"),
                {"id": job_id, "error": str(exc)[:1000]},
            )
            await session.commit()



@router.get("/brands", dependencies=[Depends(require_permission("brand:read"))])
async def list_admin_brands(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=120),
    status_filter: str = Query(default="all", alias="status"),
    session: AsyncSession = Depends(get_session),
) -> dict:
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
    total = (
        await session.execute(text(f"SELECT COUNT(*) FROM brands b {where_sql}"), params)
    ).scalar_one()
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
                b.seo_title AS "seoTitle",
                b.seo_description AS "seoDescription",
                b.sort_order AS "order",
                b.is_active AS "isActive",
                b.created_at AS "createdAt",
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
    return {
        "items": [dict(row._mapping) for row in result],
        "page": page,
        "limit": limit,
        "total": total,
    }


async def sync_brand_categories(session: AsyncSession, brand_id: UUID, category_ids: list[UUID]) -> None:
    if category_ids:
        valid_count = (
            await session.execute(
                text("SELECT COUNT(*) FROM categories WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
                {"ids": category_ids},
            )
        ).scalar_one()
        if valid_count != len(set(category_ids)):
            raise HTTPException(status_code=400, detail="One or more categories do not exist.")
    await session.execute(text("DELETE FROM brand_categories WHERE brand_id = :brand_id"), {"brand_id": brand_id})
    for category_id in category_ids:
        await session.execute(
            text("INSERT INTO brand_categories (brand_id, category_id) VALUES (:brand_id, :category_id) ON CONFLICT DO NOTHING"),
            {"brand_id": brand_id, "category_id": category_id},
        )


async def ensure_brand_code_available(session: AsyncSession, code: str, exclude_id: UUID | None = None) -> None:
    row = (
        await session.execute(
            text(
                """
                SELECT id
                FROM brands
                WHERE lower(code) = lower(:code)
                  AND (:exclude_id IS NULL OR id != :exclude_id)
                """
            ),
            {"code": code.strip(), "exclude_id": exclude_id},
        )
    ).first()
    if row:
        raise HTTPException(status_code=409, detail="Mã thương hiệu đã tồn tại.")


async def ensure_brand_slug_available(session: AsyncSession, slug: str, exclude_id: UUID | None = None) -> None:
    row = (
        await session.execute(
            text(
                """
                SELECT id
                FROM brands
                WHERE lower(slug) = lower(:slug)
                  AND (:exclude_id IS NULL OR id != :exclude_id)
                """
            ),
            {"slug": slug.strip(), "exclude_id": exclude_id},
        )
    ).first()
    if row:
        raise HTTPException(status_code=409, detail="Slug thương hiệu đã tồn tại.")


async def invalidate_brand_cache(redis: Redis, *slugs: str | None) -> None:
    return


async def resolve_redirect_chain(session: AsyncSession, slug: str, max_hops: int = 5) -> list[str]:
    chain: list[str] = []
    current = slug
    for _ in range(max_hops):
        next_slug = (
            await session.execute(
                text("SELECT new_slug FROM brand_slug_redirects WHERE old_slug = :slug"),
                {"slug": current},
            )
        ).scalar_one_or_none()
        if not next_slug:
            return chain
        chain.append(str(next_slug))
        current = str(next_slug)
    return chain


async def upsert_brand_redirect(session: AsyncSession, brand_id: UUID, old_slug: str, new_slug: str) -> None:
    if old_slug == new_slug:
        return
    chain = await resolve_redirect_chain(session, new_slug)
    if old_slug in chain or new_slug in chain:
        await session.execute(
            text("DELETE FROM brand_slug_redirects WHERE brand_id = :brand_id OR old_slug = :new_slug OR new_slug = :old_slug"),
            {"brand_id": brand_id, "new_slug": new_slug, "old_slug": old_slug},
        )
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


@router.post("/brands/check-code", dependencies=[Depends(require_permission("brand:read"))])
async def check_brand_code(payload: BrandCodeCheckPayload, session: AsyncSession = Depends(get_session)) -> dict:
    row = (
        await session.execute(
            text(
                """
                SELECT 1
                FROM brands
                WHERE lower(code) = lower(:code)
                  AND (:exclude_id IS NULL OR id != :exclude_id)
                """
            ),
            {"code": payload.code.strip(), "exclude_id": payload.excludeId},
        )
    ).first()
    return {"available": row is None}


@router.post("/brands", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("brand:create"))])
async def create_brand(
    payload: BrandPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    ensure_not_data_url(payload.logoUrl, "logoUrl")
    brand_id = uuid4()
    code = payload.code.strip()
    slug = slugify(payload.slug or payload.name)
    await ensure_brand_code_available(session, code)
    await ensure_brand_slug_available(session, slug)
    await session.execute(
        text(
            """
            INSERT INTO brands (
                id, code, slug, name, logo_url, logo_alt_text, landing_title, seo_title, seo_description, sort_order, is_active
            )
            VALUES (
                :id, :code, :slug, :name, :logo_url, :logo_alt_text, :landing_title, :seo_title, :seo_description, :sort_order, :is_active
            )
            """
        ),
        {
            "id": brand_id,
            "code": code,
            "slug": slug,
            "name": payload.name,
            "logo_url": payload.logoUrl,
            "logo_alt_text": payload.logoAltText,
            "landing_title": payload.landingTitle,
            "seo_title": payload.seoTitle,
            "seo_description": payload.seoDescription,
            "sort_order": payload.order,
            "is_active": payload.isActive,
        },
    )
    await sync_brand_categories(session, brand_id, payload.categoryIds)
    await session.commit()
    await invalidate_brand_cache(redis, slug)
    return {"id": str(brand_id)}


@router.patch("/brands/{brand_id}", dependencies=[Depends(require_permission("brand:update"))])
async def update_brand(
    brand_id: UUID,
    payload: BrandPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    ensure_not_data_url(payload.logoUrl, "logoUrl")
    old_brand = (
        await session.execute(text("SELECT slug FROM brands WHERE id = :id"), {"id": brand_id})
    ).mappings().first()
    if not old_brand:
        raise HTTPException(status_code=404, detail="Brand not found.")
    code = payload.code.strip()
    slug = slugify(payload.slug or payload.name)
    await ensure_brand_code_available(session, code, brand_id)
    await ensure_brand_slug_available(session, slug, brand_id)
    result = await session.execute(
        text(
            """
            UPDATE brands
                SET code = :code, slug = :slug, name = :name, logo_url = :logo_url, logo_alt_text = :logo_alt_text,
                landing_title = :landing_title, seo_title = :seo_title, seo_description = :seo_description,
                sort_order = :sort_order, is_active = :is_active, updated_at = NOW()
            WHERE id = :id
            """
        ),
        {
            "id": brand_id,
            "code": code,
            "slug": slug,
            "name": payload.name,
            "logo_url": payload.logoUrl,
            "logo_alt_text": payload.logoAltText,
            "landing_title": payload.landingTitle,
            "seo_title": payload.seoTitle,
            "seo_description": payload.seoDescription,
            "sort_order": payload.order,
            "is_active": payload.isActive,
        },
    )
    if old_brand["slug"] and old_brand["slug"] != slug:
        await upsert_brand_redirect(session, brand_id, old_brand["slug"], slug)
    await sync_brand_categories(session, brand_id, payload.categoryIds)
    await audit_brand_event(
        session,
        "BRAND_UPDATED",
        {"brandId": str(brand_id), "oldSlug": old_brand["slug"], "newSlug": slug, "code": code, "name": payload.name},
        current_user_id,
    )
    await bump_brand_cache_versions(session, old_brand["slug"], slug)
    await session.commit()
    await invalidate_brand_cache(redis, old_brand["slug"], slug)
    return {"ok": True}


@router.post("/brands/import", dependencies=[Depends(require_permission("brand:create"))])
async def import_brands(
    mode: str = Form(default="skip"),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    if mode not in {"skip", "upsert"}:
        raise HTTPException(status_code=400, detail="Mode must be skip or upsert.")
    filename = file.filename or "brands.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file CSV.")
    import_dir = Path(settings.brand_import_dir)
    if not import_dir.is_absolute():
        import_dir = Path.cwd() / import_dir
    import_dir.mkdir(parents=True, exist_ok=True)
    job_file_id = uuid4()
    source_path = import_dir / f"{job_file_id}.csv"
    size = 0
    with source_path.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > 50 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="File import vượt quá 50MB.")
            output.write(chunk)
    with source_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.reader(csv_file))
    total_rows = len(rows)
    if rows and rows[0] and rows[0][0].strip().lower() in {"tên", "ten", "name"}:
        total_rows -= 1
    if total_rows <= 0:
        raise HTTPException(status_code=400, detail="File cần có ít nhất một dòng dữ liệu.")
    job_id = await enqueue_brand_import_job(
        session,
        redis,
        source_path=str(source_path),
        total_rows=total_rows,
        mode=mode,
        source_filename=filename,
        user_id=current_user_id,
    )
    await session.commit()
    return {"jobId": str(job_id), "status": "QUEUED"}

    job_id = uuid4()
    imported = 0
    updated = 0
    skipped: list[dict] = []
    changed_slugs: list[str] = []
    seen_codes: set[str] = set()
    for index, item in enumerate(payload.items, start=1):
        ensure_not_data_url(item.logoUrl, "logoUrl")
        brand_id = uuid4()
        code = item.code.strip()
        if code.lower() in seen_codes:
            skipped.append({"row": index, "name": item.name, "reason": "Mã bị trùng trong file import."})
            continue
        seen_codes.add(code.lower())
        exists = (
            await session.execute(
                text("SELECT id, slug FROM brands WHERE lower(code) = lower(:code)"),
                {"code": code},
            )
        ).mappings().first()
        if exists:
            if payload.mode == "skip":
                skipped.append({"row": index, "name": item.name, "code": code, "reason": "Mã thương hiệu đã tồn tại."})
                continue
            await session.execute(
                text(
                    """
                    UPDATE brands
                    SET name = :name, logo_url = COALESCE(:logo_url, logo_url),
                        sort_order = :sort_order, updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"id": exists["id"], "name": item.name.strip(), "logo_url": item.logoUrl, "sort_order": item.order},
            )
            updated += 1
            changed_slugs.append(exists["slug"])
            continue
        result = await session.execute(
            text(
                """
                INSERT INTO brands (id, code, slug, name, logo_url, sort_order, is_active)
                VALUES (:id, :code, :slug, :name, :logo_url, :sort_order, TRUE)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {
                "id": brand_id,
                "code": code,
                "slug": f"{slugify(item.name)}-{brand_id.hex[:5]}",
                "name": item.name.strip(),
                "logo_url": item.logoUrl,
                "sort_order": item.order,
            },
        )
        if result.rowcount:
            imported += 1
            changed_slugs.append(f"{slugify(item.name)}-{brand_id.hex[:5]}")
        else:
            skipped.append({"row": index, "name": item.name, "reason": "Tên thương hiệu đã tồn tại."})
    await session.execute(
        text(
            """
            INSERT INTO brand_import_jobs (
                id, mode, source_filename, total_rows, imported_rows, updated_rows, skipped_rows, status, report
            )
            VALUES (
                :id, :mode, :source_filename, :total_rows, :imported_rows, :updated_rows, :skipped_rows, 'COMPLETED', CAST(:report AS jsonb)
            )
            """
        ),
        {
            "id": job_id,
            "mode": payload.mode,
            "source_filename": payload.sourceFilename,
            "total_rows": len(payload.items),
            "imported_rows": imported,
            "updated_rows": updated,
            "skipped_rows": len(skipped),
            "report": json.dumps(skipped, ensure_ascii=False),
        },
    )
    await session.commit()
    await invalidate_brand_cache(redis, *changed_slugs)
    return {"jobId": str(job_id), "imported": imported, "updated": updated, "skipped": skipped}


@router.get("/brands/import-jobs", dependencies=[Depends(require_permission("brand:read"))])
async def list_brand_import_jobs(session: AsyncSession = Depends(get_session)) -> list[dict]:
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


@router.get("/brands/import-jobs/{job_id}", dependencies=[Depends(require_permission("brand:read"))])
async def get_brand_import_job(
    job_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    forwarded = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    rate_key = f"rate:brand-import-job:{client_ip}:{job_id}"
    try:
        count = await redis.incr(rate_key)
        if count == 1:
            await redis.expire(rate_key, 60)
        if count > 30:
            raise HTTPException(status_code=429, detail="Bạn đang kiểm tra tiến trình quá thường xuyên.")
    except HTTPException:
        raise
    except Exception:
        pass


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
    if not row:
        raise HTTPException(status_code=404, detail="Import job not found.")
    return dict(row)


@router.patch("/brands/{brand_id}/status", dependencies=[Depends(require_permission("brand:update"))])
async def update_brand_status(
    brand_id: UUID,
    payload: BrandStatusPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    brand = (
        await session.execute(text("SELECT slug FROM brands WHERE id = :id"), {"id": brand_id})
    ).mappings().first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found.")
    result = await session.execute(
        text("UPDATE brands SET is_active = :is_active, updated_at = NOW() WHERE id = :id"),
        {"id": brand_id, "is_active": payload.isActive},
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Brand not found.")
    job_id = None
    if not payload.isActive:
        job_id = uuid4()
        await session.execute(
            text(
                """
                INSERT INTO brand_status_jobs (id, brand_id, target_is_active, status)
                VALUES (:id, :brand_id, FALSE, 'PENDING')
                """
            ),
            {"id": job_id, "brand_id": brand_id},
        )
    await audit_brand_event(
        session,
        "BRAND_STATUS_CHANGED",
        {"brandIds": [str(brand_id)], "isActive": payload.isActive},
        current_user_id,
    )
    await bump_brand_cache_versions(session, brand["slug"])
    await session.commit()
    await invalidate_brand_cache(redis, brand["slug"])
    if job_id:
        background_tasks.add_task(process_brand_status_job, job_id, brand_id, payload.isActive)
        return {"ok": True, "action": "deactivated", "status": "PROCESSING", "jobId": str(job_id)}
    return {"ok": True, "action": "activated"}


@router.patch("/brands/status", dependencies=[Depends(require_permission("brand:update"))])
async def update_brands_status(
    payload: BrandBulkStatusPayload,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    rows = (
        await session.execute(
            text("SELECT id, slug FROM brands WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": payload.ids},
        )
    ).mappings().all()
    found_ids = {row["id"] for row in rows}
    failed = [{"id": str(brand_id), "reason": "Brand not found."} for brand_id in payload.ids if brand_id not in found_ids]
    if rows:
        await session.execute(
            text("UPDATE brands SET is_active = :is_active, updated_at = NOW() WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": [row["id"] for row in rows], "is_active": payload.isActive},
        )
        await audit_brand_event(
            session,
            "BRAND_STATUS_CHANGED",
            {"brandIds": [str(row["id"]) for row in rows], "isActive": payload.isActive, "bulk": True},
            current_user_id,
        )
        await bump_brand_cache_versions(session, *[row["slug"] for row in rows])
        await session.commit()
        await invalidate_brand_cache(redis, *[row["slug"] for row in rows])
    return {"updated": len(rows), "failed": failed}


@router.get("/brands/status-jobs", dependencies=[Depends(require_permission("brand:read"))])
async def list_brand_status_jobs(session: AsyncSession = Depends(get_session)) -> list[dict]:
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


@router.delete("/brands/{brand_id}", dependencies=[Depends(require_permission("brand:delete"))])
async def deactivate_brand(
    brand_id: UUID,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    current_user_id: UUID = Depends(get_current_user_id),
) -> dict:
    brand = (
        await session.execute(
            text("SELECT id::text, code, slug, name FROM brands WHERE id = :id"),
            {"id": brand_id},
        )
    ).mappings().first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found.")
    product_count = (
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
    if product_count > 0:
        raise HTTPException(status_code=409, detail="Không thể xóa thương hiệu đang có sản phẩm. Hãy ẩn thương hiệu nếu cần.")

    result = await session.execute(text("DELETE FROM brands WHERE id = :id"), {"id": brand_id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Brand not found.")
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs (user_id, event_type, metadata)
            VALUES (:user_id, 'BRAND_HARD_DELETED', CAST(:metadata AS jsonb))
            """
        ),
        {"user_id": current_user_id, "metadata": json.dumps({"brand": dict(brand)}, ensure_ascii=False)},
    )
    await session.commit()
    await invalidate_brand_cache(redis, brand["slug"])
    return {"ok": True, "action": "deleted"}


