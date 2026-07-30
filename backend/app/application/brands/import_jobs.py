import csv
import json
import os
import unicodedata
from pathlib import Path
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import brand_repo

BRAND_IMPORT_QUEUE = "queue:brand_import"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.strip()).replace("đ", "d").replace("Đ", "D")
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in normalized)
    return "-".join(part for part in slug.split("-") if part) or uuid4().hex[:8]


async def invalidate_brand_cache(redis: Redis, *slugs: str | None) -> None:
    return


async def bump_brand_cache_versions(session: AsyncSession, *slugs: str | None) -> None:
    values = [slug for slug in {item for item in slugs if item}]
    await brand_repo.bump_brand_cache_versions(session, values)


async def audit_brand_event(
    session: AsyncSession,
    event_type: str,
    metadata: dict,
    user_id: UUID | None = None,
) -> None:
    await brand_repo.audit_brand_event(session, event_type=event_type, metadata=metadata, user_id=user_id)


async def enqueue_brand_import_job(
    session: AsyncSession,
    redis: Redis,
    *,
    items: list[dict] | None = None,
    source_path: str | None = None,
    total_rows: int | None = None,
    mode: str,
    source_filename: str | None,
    user_id: UUID | None,
) -> UUID:
    job_id = uuid4()
    row_count = total_rows if total_rows is not None else len(items or [])
    await brand_repo.create_brand_import_job(
        session,
        job_id=job_id,
        items=items or [],
        source_path=source_path,
        total_rows=row_count,
        mode=mode,
        source_filename=source_filename,
        user_id=user_id,
    )
    await audit_brand_event(
        session,
        "BRAND_IMPORT_QUEUED",
        {"jobId": str(job_id), "mode": mode, "sourceFilename": source_filename, "totalRows": row_count},
        user_id,
    )
    await redis.rpush(BRAND_IMPORT_QUEUE, str(job_id))
    return job_id


def _load_items_from_csv(source_path: str) -> list[dict]:
    with Path(source_path).open("r", encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.reader(csv_file))
    if rows and rows[0] and rows[0][0].strip().lower() in {"tên", "ten", "name"}:
        rows = rows[1:]
    return [
        {
            "name": row[0].strip() if len(row) > 0 else "",
            "code": row[1].strip() if len(row) > 1 else "",
            "logoUrl": row[2].strip() if len(row) > 2 else None,
            "order": int(row[3]) if len(row) > 3 and str(row[3]).strip().isdigit() else 0,
        }
        for row in rows
        if any(str(cell).strip() for cell in row)
    ]


async def process_brand_import_job(session: AsyncSession, redis: Redis, job_id: UUID) -> None:
    source_path: str | None = None
    job = await brand_repo.get_brand_import_job_for_update(session, job_id)
    if not job:
        return
    if job["status"] not in {"QUEUED", "FAILED"}:
        return

    payload = job["payload"] or {}
    if isinstance(payload, str):
        payload = json.loads(payload)
    items = payload.get("items") or []
    source_path = job.get("source_path")
    if source_path:
        items = _load_items_from_csv(source_path)

    requested_by = payload.get("requestedBy")
    user_id = UUID(requested_by) if requested_by else None
    total_rows = int(job["total_rows"] or len(items))

    await brand_repo.mark_brand_import_job_processing(session, job_id)
    await session.commit()

    imported = 0
    updated = 0
    skipped: list[dict] = []
    changed_slugs: list[str] = []
    seen_codes: set[str] = set()
    seen_names: set[str] = set()

    try:
        for index, item in enumerate(items, start=1):
            name = str(item.get("name") or "").strip()
            code = str(item.get("code") or "").strip()
            logo_url = item.get("logoUrl") or None
            order = int(item.get("order") or 0)
            normalized_name = name.casefold()
            normalized_code = code.casefold()

            if not name or not code:
                skipped.append({"row": index, "name": name, "code": code, "reason": "Thiếu tên hoặc mã thương hiệu."})
            elif normalized_code in seen_codes:
                skipped.append({"row": index, "name": name, "code": code, "reason": "Mã bị trùng trong file import."})
            elif normalized_name in seen_names:
                skipped.append({"row": index, "name": name, "code": code, "reason": "Tên thương hiệu bị trùng trong file import."})
            else:
                seen_codes.add(normalized_code)
                seen_names.add(normalized_name)
                exists = await brand_repo.get_brand_by_code(session, code)
                if exists and job["mode"] == "skip":
                    skipped.append({"row": index, "name": name, "code": code, "reason": "Mã thương hiệu đã tồn tại."})
                elif await brand_repo.brand_name_exists(session, name=name, exclude_id=exists["id"] if exists else None):
                    skipped.append({"row": index, "name": name, "code": code, "reason": "Tên thương hiệu đã tồn tại."})
                else:
                    brand_id = uuid4()
                    slug = f"{slugify(name)}-{brand_id.hex[:5]}"
                    skip_reason: str | None = None
                    try:
                        async with session.begin_nested():
                            row = await brand_repo.upsert_brand_from_import(
                                session,
                                brand_id=brand_id,
                                code=code,
                                slug=slug,
                                name=name,
                                logo_url=logo_url,
                                sort_order=order,
                                mode=job["mode"],
                            )
                    except IntegrityError:
                        row = None
                        skip_reason = "Tên hoặc mã thương hiệu đã tồn tại."
                    if row and row["inserted"]:
                        imported += 1
                        changed_slugs.append(row["slug"])
                    elif row:
                        updated += 1
                        changed_slugs.append(row["slug"])
                    else:
                        skipped.append({"row": index, "name": name, "code": code, "reason": skip_reason or "Tên thương hiệu đã tồn tại."})

            progress = int(index / max(total_rows, 1) * 100)
            await brand_repo.update_brand_import_job_progress(
                session,
                job_id=job_id,
                processed_rows=index,
                progress=progress,
                imported_rows=imported,
                updated_rows=updated,
                skipped_rows=len(skipped),
                report=skipped,
            )
            await session.commit()

        await brand_repo.mark_brand_import_job_completed(
            session,
            job_id=job_id,
            imported_rows=imported,
            updated_rows=updated,
            skipped_rows=len(skipped),
            report=skipped,
        )
        await audit_brand_event(
            session,
            "BRAND_IMPORTED",
            {
                "jobId": str(job_id),
                "mode": job["mode"],
                "sourceFilename": job["source_filename"],
                "totalRows": total_rows,
                "importedRows": imported,
                "updatedRows": updated,
                "skippedRows": len(skipped),
            },
            user_id,
        )
        await session.commit()
        await bump_brand_cache_versions(session, *changed_slugs)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        await brand_repo.mark_brand_import_job_failed(session, job_id=job_id, error_message=str(exc))
        await session.commit()
        raise
    finally:
        if source_path:
            try:
                os.remove(source_path)
            except FileNotFoundError:
                pass
