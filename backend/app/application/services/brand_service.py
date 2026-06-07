import csv
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.admin import (
    BrandBulkStatusPayload,
    BrandCodeCheckPayload,
    BrandPayload,
    BrandStatusPayload,
)
from app.shared.admin_utils import ensure_not_data_url, slugify
from app.application.brands.import_jobs import audit_brand_event, bump_brand_cache_versions, enqueue_brand_import_job
from app.config import settings
from app.infrastructure.database.repositories import brand_repo
from app.infrastructure.database.session import AsyncSessionFactory


async def process_brand_status_job(job_id: UUID, brand_id: UUID, target_is_active: bool) -> None:
    async with AsyncSessionFactory() as session:
        try:
            await brand_repo.mark_status_job_processing(session, job_id)
            total = await brand_repo.count_brand_products(session, brand_id)
            await brand_repo.update_status_job_total(session, job_id=job_id, total=total)
            if not target_is_active:
                product_rows = await brand_repo.list_active_product_ids_by_brand(session, brand_id)
                for index in range(0, len(product_rows), 100):
                    chunk = product_rows[index:index + 100]
                    if not chunk:
                        continue
                    await brand_repo.hide_products_by_brand(session, chunk)
                    await brand_repo.increment_status_job_processed(session, job_id=job_id, count=len(chunk))
                    await session.commit()
            else:
                restored = await brand_repo.restore_products_hidden_by_brand(session, brand_id)
                await brand_repo.increment_status_job_processed(session, job_id=job_id, count=restored)
                await session.commit()
            await brand_repo.mark_status_job_completed(session, job_id)
            await session.commit()
        except Exception as exc:
            await brand_repo.mark_status_job_failed(session, job_id=job_id, error=str(exc))
            await session.commit()

async def sync_brand_categories(session: AsyncSession, brand_id: UUID, category_ids: list[UUID]) -> None:
    if category_ids:
        valid_count = await brand_repo.count_existing_categories(session, category_ids)
        if valid_count != len(set(category_ids)):
            raise HTTPException(status_code=400, detail="One or more categories do not exist.")
    await brand_repo.delete_brand_categories(session, brand_id)
    for category_id in category_ids:
        await brand_repo.insert_brand_category(session, brand_id=brand_id, category_id=category_id)

async def ensure_brand_code_available(session: AsyncSession, code: str, exclude_id: UUID | None = None) -> None:
    if await brand_repo.brand_code_exists(session, code=code, exclude_id=exclude_id):
        raise HTTPException(status_code=409, detail="M? th??ng hi?u ?? t?n t?i.")

async def ensure_brand_slug_available(session: AsyncSession, slug: str, exclude_id: UUID | None = None) -> None:
    if await brand_repo.brand_slug_exists(session, slug=slug, exclude_id=exclude_id):
        raise HTTPException(status_code=409, detail="Slug th??ng hi?u ?? t?n t?i.")

async def invalidate_brand_cache(redis: Redis, *slugs: str | None) -> None:
    return


async def resolve_redirect_chain(session: AsyncSession, slug: str, max_hops: int = 5) -> list[str]:
    chain: list[str] = []
    current = slug
    for _ in range(max_hops):
        next_slug = await brand_repo.get_redirect_new_slug(session, current)
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
        await brand_repo.delete_brand_redirect_conflicts(session, brand_id=brand_id, old_slug=old_slug, new_slug=new_slug)
    await brand_repo.upsert_brand_redirect(session, brand_id=brand_id, old_slug=old_slug, new_slug=new_slug)

async def list_admin_brands(
    session: AsyncSession,
    page: int = 1,
    limit: int = 50,
    search: str | None = None,
    status_filter: str = "all",
) -> dict:
    return await brand_repo.list_admin_brands(session, page=page, limit=limit, search=search, status_filter=status_filter)

async def check_brand_code(payload: BrandCodeCheckPayload, session: AsyncSession) -> dict:
    return {"available": await brand_repo.is_brand_code_available(session, code=payload.code, exclude_id=payload.excludeId)}

async def create_brand(
    payload: BrandPayload,
    session: AsyncSession,
    redis: Redis,
) -> dict:
    ensure_not_data_url(payload.logoUrl, "logoUrl")
    brand_id = uuid4()
    code = payload.code.strip()
    slug = slugify(payload.slug or payload.name)
    await ensure_brand_code_available(session, code)
    await ensure_brand_slug_available(session, slug)
    await brand_repo.insert_brand(
        session,
        brand_id=brand_id,
        code=code,
        slug=slug,
        name=payload.name,
        logo_url=payload.logoUrl,
        logo_alt_text=payload.logoAltText,
        landing_title=payload.landingTitle,
        sort_order=payload.order,
        is_active=payload.isActive,
    )
    await sync_brand_categories(session, brand_id, payload.categoryIds)
    await session.commit()
    await invalidate_brand_cache(redis, slug)
    return {"id": str(brand_id)}

async def update_brand(
    brand_id: UUID,
    payload: BrandPayload,
    session: AsyncSession,
    redis: Redis,
    current_user_id: UUID,
) -> dict:
    ensure_not_data_url(payload.logoUrl, "logoUrl")
    old_brand = await brand_repo.get_brand_slug(session, brand_id)
    if not old_brand:
        raise HTTPException(status_code=404, detail="Brand not found.")
    code = payload.code.strip()
    slug = slugify(payload.slug or payload.name)
    await ensure_brand_code_available(session, code, brand_id)
    await ensure_brand_slug_available(session, slug, brand_id)
    await brand_repo.update_brand(
        session,
        brand_id=brand_id,
        code=code,
        slug=slug,
        name=payload.name,
        logo_url=payload.logoUrl,
        logo_alt_text=payload.logoAltText,
        landing_title=payload.landingTitle,
        sort_order=payload.order,
        is_active=payload.isActive,
    )
    if old_brand["slug"] and old_brand["slug"] != slug:
        await upsert_brand_redirect(session, brand_id, old_brand["slug"], slug)
    await sync_brand_categories(session, brand_id, payload.categoryIds)
    if old_brand["is_active"] and not payload.isActive:
        product_ids = await brand_repo.list_active_product_ids_by_brand(session, brand_id)
        if product_ids:
            await brand_repo.hide_products_by_brand(session, product_ids)
    elif not old_brand["is_active"] and payload.isActive:
        await brand_repo.restore_products_hidden_by_brand(session, brand_id)
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

async def import_brands(
    mode: str,
    file: UploadFile,
    session: AsyncSession,
    redis: Redis,
    current_user_id: UUID,
) -> dict:
    if mode not in {"skip", "upsert"}:
        raise HTTPException(status_code=400, detail="Mode must be skip or upsert.")
    filename = file.filename or "brands.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Chá»‰ há»— trá»£ file CSV.")
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
                raise HTTPException(status_code=413, detail="File import vÆ°á»£t quÃ¡ 50MB.")
            output.write(chunk)
    with source_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.reader(csv_file))
    total_rows = len(rows)
    if rows and rows[0] and rows[0][0].strip().lower() in {"tÃªn", "ten", "name"}:
        total_rows -= 1
    if total_rows <= 0:
        raise HTTPException(status_code=400, detail="File cáº§n cÃ³ Ã­t nháº¥t má»™t dÃ²ng dá»¯ liá»‡u.")
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


async def list_brand_import_jobs(session: AsyncSession) -> list[dict]:
    return await brand_repo.list_brand_import_jobs(session)

async def get_brand_import_job(
    job_id: UUID,
    client_ip: str,
    session: AsyncSession,
    redis: Redis,
) -> dict:
    rate_key = f"rate:brand-import-job:{client_ip}:{job_id}"
    try:
        count = await redis.incr(rate_key)
        if count == 1:
            await redis.expire(rate_key, 60)
        if count > 30:
            raise HTTPException(status_code=429, detail="B?n ?ang ki?m tra ti?n tr?nh qu? th??ng xuy?n.")
    except HTTPException:
        raise
    except Exception:
        pass

    row = await brand_repo.get_brand_import_job(session, job_id)
    if not row:
        raise HTTPException(status_code=404, detail="Import job not found.")
    return row

async def update_brand_status(
    brand_id: UUID,
    payload: BrandStatusPayload,
    background_tasks: BackgroundTasks,
    session: AsyncSession,
    redis: Redis,
    current_user_id: UUID,
) -> dict:
    brand = await brand_repo.get_brand_slug(session, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found.")
    updated = await brand_repo.update_brand_status(session, brand_id=brand_id, is_active=payload.isActive)
    if updated == 0:
        raise HTTPException(status_code=404, detail="Brand not found.")
    job_id = None
    if not payload.isActive:
        job_id = uuid4()
        await brand_repo.create_brand_status_job(session, job_id=job_id, brand_id=brand_id)
    else:
        job_id = uuid4()
        await brand_repo.create_brand_status_job(session, job_id=job_id, brand_id=brand_id, target_is_active=True)
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
        action = "activated" if payload.isActive else "deactivated"
        return {"ok": True, "action": action, "status": "PROCESSING", "jobId": str(job_id)}
    return {"ok": True, "action": "activated"}

async def update_brands_status(
    payload: BrandBulkStatusPayload,
    session: AsyncSession,
    redis: Redis,
    current_user_id: UUID,
) -> dict:
    rows = await brand_repo.list_brands_by_ids(session, payload.ids)
    found_ids = {row["id"] for row in rows}
    failed = [{"id": str(brand_id), "reason": "Brand not found."} for brand_id in payload.ids if brand_id not in found_ids]
    if rows:
        await brand_repo.update_brands_status(session, brand_ids=[row["id"] for row in rows], is_active=payload.isActive)
        for row in rows:
            if payload.isActive:
                await brand_repo.restore_products_hidden_by_brand(session, row["id"])
            else:
                product_ids = await brand_repo.list_active_product_ids_by_brand(session, row["id"])
                if product_ids:
                    await brand_repo.hide_products_by_brand(session, product_ids)
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

async def list_brand_status_jobs(session: AsyncSession) -> list[dict]:
    return await brand_repo.list_brand_status_jobs(session)

async def deactivate_brand(
    brand_id: UUID,
    session: AsyncSession,
    redis: Redis,
    current_user_id: UUID,
) -> dict:
    brand = await brand_repo.get_brand_for_delete(session, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found.")
    product_count = await brand_repo.count_products_for_brand_delete(session, brand_id)
    if product_count > 0:
        raise HTTPException(status_code=409, detail="Kh?ng th? x?a th??ng hi?u ?ang c? s?n ph?m. H?y ?n th??ng hi?u n?u c?n.")

    deleted = await brand_repo.delete_brand(session, brand_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Brand not found.")
    await brand_repo.audit_brand_hard_deleted(session, user_id=current_user_id, brand=brand)
    await session.commit()
    await invalidate_brand_cache(redis, brand["slug"])
    return {"ok": True, "action": "deleted"}
