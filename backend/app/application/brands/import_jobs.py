import json
import os
import csv
import unicodedata
from pathlib import Path
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

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
    if not values:
        return
    await session.execute(
        text("UPDATE brands SET cache_version = cache_version + 1 WHERE slug IN :slugs").bindparams(bindparam("slugs", expanding=True)),
        {"slugs": values},
    )


async def audit_brand_event(
    session: AsyncSession,
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
            "total_rows": total_rows if total_rows is not None else len(items or []),
            "payload": json.dumps({"items": items or [], "requestedBy": str(user_id) if user_id else None}, ensure_ascii=False),
            "source_path": source_path,
        },
    )
    await audit_brand_event(
        session,
        "BRAND_IMPORT_QUEUED",
        {"jobId": str(job_id), "mode": mode, "sourceFilename": source_filename, "totalRows": total_rows if total_rows is not None else len(items or [])},
        user_id,
    )
    await redis.rpush(BRAND_IMPORT_QUEUE, str(job_id))
    return job_id


async def process_brand_import_job(session: AsyncSession, redis: Redis, job_id: UUID) -> None:
    source_path: str | None = None
    job = (
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
        with Path(source_path).open("r", encoding="utf-8-sig", newline="") as csv_file:
            rows = list(csv.reader(csv_file))
        if rows and rows[0] and rows[0][0].strip().lower() in {"tên", "ten", "name"}:
            rows = rows[1:]
        items = [
            {
                "name": row[0].strip() if len(row) > 0 else "",
                "code": row[1].strip() if len(row) > 1 else "",
                "logoUrl": row[2].strip() if len(row) > 2 else None,
                "order": int(row[3]) if len(row) > 3 and str(row[3]).strip().isdigit() else 0,
            }
            for row in rows
            if any(str(cell).strip() for cell in row)
        ]
    requested_by = payload.get("requestedBy")
    user_id = UUID(requested_by) if requested_by else None
    total_rows = int(job["total_rows"] or len(items))

    await session.execute(
        text("UPDATE brand_import_jobs SET status = 'PROCESSING', started_at = NOW(), error_message = NULL WHERE id = :id"),
        {"id": job_id},
    )
    await session.commit()

    imported = 0
    updated = 0
    skipped: list[dict] = []
    changed_slugs: list[str] = []
    seen_codes: set[str] = set()

    try:
        for index, item in enumerate(items, start=1):
            name = str(item.get("name") or "").strip()
            code = str(item.get("code") or "").strip()
            logo_url = item.get("logoUrl") or None
            order = int(item.get("order") or 0)
            if not name or not code:
                skipped.append({"row": index, "name": name, "code": code, "reason": "Thiếu tên hoặc mã thương hiệu."})
            elif code.lower() in seen_codes:
                skipped.append({"row": index, "name": name, "code": code, "reason": "Mã bị trùng trong file import."})
            else:
                seen_codes.add(code.lower())
                exists = (
                    await session.execute(
                        text("SELECT id, slug FROM brands WHERE lower(code) = lower(:code)"),
                        {"code": code},
                    )
                ).mappings().first()
                if exists and job["mode"] == "skip":
                    skipped.append({"row": index, "name": name, "code": code, "reason": "Mã thương hiệu đã tồn tại."})
                else:
                    brand_id = uuid4()
                    slug = f"{slugify(name)}-{brand_id.hex[:5]}"
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
                            "sort_order": order,
                            "mode": job["mode"],
                        },
                        )
                    ).mappings().first()
                    if row and row["inserted"]:
                        imported += 1
                        changed_slugs.append(row["slug"])
                    elif row:
                        updated += 1
                        changed_slugs.append(row["slug"])
                    else:
                        skipped.append({"row": index, "name": name, "code": code, "reason": "Tên thương hiệu đã tồn tại."})

            progress = int(index / max(total_rows, 1) * 100)
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
                    "processed_rows": index,
                    "progress": progress,
                    "imported_rows": imported,
                    "updated_rows": updated,
                    "skipped_rows": len(skipped),
                    "report": json.dumps(skipped, ensure_ascii=False),
                },
            )
            await session.commit()

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
                "imported_rows": imported,
                "updated_rows": updated,
                "skipped_rows": len(skipped),
                "report": json.dumps(skipped, ensure_ascii=False),
            },
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
        await session.execute(
            text(
                """
                UPDATE brand_import_jobs
                SET status = 'FAILED', error_message = :error_message, completed_at = NOW()
                WHERE id = :id
                """
            ),
            {"id": job_id, "error_message": str(exc)},
        )
        await session.commit()
        raise
    finally:
        if source_path:
            try:
                os.remove(source_path)
            except FileNotFoundError:
                pass
