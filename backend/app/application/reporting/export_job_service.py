import asyncio
import csv
import logging
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories.reporting import export_jobs as export_job_repo
from app.infrastructure.database.session import AsyncSessionFactory

from .authorization import (
    accessible_export_report_types,
    ensure_report_type_access,
)
from .customer_report_service import get_customer_report
from .export_service import (
    REPORT_CSV_HEADERS,
    _safe_cell,
    report_csv_rows,
)
from .order_report_service import get_order_report
from .period import build_report_period
from .revenue_service import get_revenue_report


EXPORT_DIRECTORY = Path(__file__).resolve().parents[3] / "exports" / "reports"
EXPORT_LIFETIME = timedelta(hours=24)
EXPORT_BATCH_SIZE = 500
EXPORT_MAX_ATTEMPTS = 3
EXPORT_RETRY_DELAY_SECONDS = 30
EXPORT_HEARTBEAT_INTERVAL_SECONDS = 30
ORPHAN_EXPORT_MIN_AGE = EXPORT_LIFETIME + timedelta(hours=1)
MAX_ACTIVE_EXPORTS_PER_USER = 3
logger = logging.getLogger("ecommerce_app.reporting")
TOKENIZED_EXPORT_FILENAME = re.compile(
    r"^(revenue|orders|customers)-"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.csv$",
    re.IGNORECASE,
)


class ReportExportLeaseLost(RuntimeError):
    pass


async def _maintain_export_job_lease(
    *,
    job_id: UUID,
    claim_token: UUID,
    stop_event: asyncio.Event,
    lease_lost_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=EXPORT_HEARTBEAT_INTERVAL_SECONDS,
            )
            return
        except TimeoutError:
            pass

        try:
            async with AsyncSessionFactory() as heartbeat_session:
                refreshed = await export_job_repo.refresh_export_job_heartbeat(
                    heartbeat_session,
                    job_id=job_id,
                    claim_token=claim_token,
                )
                await heartbeat_session.commit()
        except Exception:
            logger.error(
                "report_export_heartbeat_failed",
                extra={
                    "event": "report_export_heartbeat_failed",
                    "job_id": str(job_id),
                },
                exc_info=True,
            )
            continue

        if not refreshed:
            lease_lost_event.set()
            return


def _ensure_export_job_lease(lease_lost_event: asyncio.Event) -> None:
    if lease_lost_event.is_set():
        raise ReportExportLeaseLost("Tác vụ xuất báo cáo không còn thuộc worker hiện tại.")


def _order_filter_kwargs(filters: dict) -> dict:
    return {
        "date_basis": filters.get("dateBasis", "createdAt"),
        "status": filters.get("status"),
        "channel": filters.get("channel"),
        "payment_method": filters.get("paymentMethod"),
        "payment_status": filters.get("paymentStatus"),
        "fulfillment_method": filters.get("fulfillmentMethod"),
        "search": filters.get("search"),
    }


def _customer_filter_kwargs(filters: dict) -> dict:
    return {
        "tier": filters.get("tier"),
        "segment": filters.get("segment"),
        "search": filters.get("search"),
    }


async def create_report_export_job(
    session: AsyncSession,
    *,
    requested_by: UUID,
    report_type: str,
    filters: dict,
) -> dict:
    await export_job_repo.lock_export_queue_for_user(session, requested_by)
    active_jobs = await export_job_repo.count_active_export_jobs(
        session,
        requested_by,
    )
    if active_jobs >= MAX_ACTIVE_EXPORTS_PER_USER:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Bạn đang có quá nhiều tác vụ xuất đang chờ xử lý. "
                "Vui lòng đợi một tác vụ hoàn tất rồi thử lại."
            ),
        )
    job_id = uuid4()
    await export_job_repo.create_export_job(
        session,
        job_id=job_id,
        requested_by=requested_by,
        report_type=report_type,
        filters=filters,
    )
    await session.commit()
    return {"jobId": str(job_id), "status": "PENDING"}


async def process_claimed_report_export_job(
    job: dict,
) -> None:
    job_id = UUID(str(job["id"]))
    claim_token = UUID(str(job["claimToken"]))
    report_type = str(job["reportType"])
    filters = dict(job["filters"])
    temporary_path: Path | None = None
    export_path: Path | None = None
    heartbeat_stop = asyncio.Event()
    lease_lost = asyncio.Event()
    heartbeat_task = asyncio.create_task(
        _maintain_export_job_lease(
            job_id=job_id,
            claim_token=claim_token,
            stop_event=heartbeat_stop,
            lease_lost_event=lease_lost,
        )
    )
    try:
        async with AsyncSessionFactory() as report_session:
            await report_session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            )
            EXPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
            filename = f"{report_type}-{job_id}.csv"
            storage_filename = f"{report_type}-{job_id}-{claim_token}.csv"
            export_path = (EXPORT_DIRECTORY / storage_filename).resolve()
            temporary_path = export_path.with_suffix(".csv.tmp")
            total_rows = await write_report_export_file(
                report_session,
                report_type,
                filters,
                temporary_path,
                lease_lost_event=lease_lost,
            )
            _ensure_export_job_lease(lease_lost)
            await report_session.rollback()

        temporary_path.replace(export_path)
        async with AsyncSessionFactory() as state_session:
            updated = await export_job_repo.mark_completed(
                state_session,
                job_id=job_id,
                claim_token=claim_token,
                total_rows=total_rows,
                file_path=str(export_path),
                filename=filename,
                expires_at=datetime.now(timezone.utc) + EXPORT_LIFETIME,
            )
            if not updated:
                await state_session.rollback()
                export_path.unlink(missing_ok=True)
                logger.warning(
                    "report_export_lease_lost",
                    extra={
                        "event": "report_export_lease_lost",
                        "job_id": str(job_id),
                    },
                )
                return
            await state_session.commit()
        logger.info(
            "report_export_completed",
            extra={
                "event": "report_export_completed",
                "job_id": str(job_id),
                "report_type": report_type,
                "attempt": job.get("attemptCount"),
                "total_rows": total_rows,
            },
        )
    except asyncio.CancelledError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        async with AsyncSessionFactory() as state_session:
            next_status = await export_job_repo.retry_or_fail_export_job(
                state_session,
                job_id=job_id,
                claim_token=claim_token,
                max_attempts=EXPORT_MAX_ATTEMPTS,
                retry_delay_seconds=EXPORT_RETRY_DELAY_SECONDS,
            )
            await state_session.commit()
        logger.error(
            "report_export_failed",
            extra={
                "event": "report_export_failed",
                "job_id": str(job_id),
                "report_type": report_type,
                "attempt": job.get("attemptCount"),
                "next_status": next_status,
                "exception_type": type(exc).__name__,
            },
            exc_info=True,
        )
    finally:
        heartbeat_stop.set()
        await heartbeat_task


def cleanup_orphaned_report_export_files(
    *,
    now: datetime | None = None,
) -> int:
    export_root = EXPORT_DIRECTORY.resolve()
    if not export_root.is_dir():
        return 0

    cutoff = (now or datetime.now(timezone.utc)) - ORPHAN_EXPORT_MIN_AGE
    removed = 0
    for path in export_root.iterdir():
        if not path.is_file() or not TOKENIZED_EXPORT_FILENAME.fullmatch(path.name):
            continue
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if modified_at > cutoff:
            continue
        path.unlink(missing_ok=True)
        removed += 1
    return removed


async def write_report_export_file(
    session: AsyncSession,
    report_type: str,
    filters: dict,
    path: Path,
    *,
    batch_size: int = EXPORT_BATCH_SIZE,
    lease_lost_event: asyncio.Event | None = None,
) -> int:
    period = build_report_period(
        from_date=date.fromisoformat(filters["from"]),
        to_date=date.fromisoformat(filters["to"]),
        timezone_name=filters.get("timezone", "Asia/Bangkok"),
        bucket="day" if report_type != "customers" else "month",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(REPORT_CSV_HEADERS[report_type])
        if report_type == "revenue":
            if lease_lost_event is not None:
                _ensure_export_job_lease(lease_lost_event)
            report = await get_revenue_report(
                session,
                period=period,
                channel=filters.get("channel"),
                payment_method=filters.get("paymentMethod"),
            )
            if lease_lost_event is not None:
                _ensure_export_job_lease(lease_lost_event)
            rows = list(report_csv_rows(report_type, report))
            writer.writerows(
                [_safe_cell(value) for value in row]
                for row in rows
            )
            return len(rows)

        filter_kwargs = (
            _order_filter_kwargs(filters)
            if report_type == "orders"
            else _customer_filter_kwargs(filters)
        )
        report_service = (
            get_order_report
            if report_type == "orders"
            else get_customer_report
        )
        page = 1
        written = 0
        total = None
        while total is None or written < total:
            if lease_lost_event is not None:
                _ensure_export_job_lease(lease_lost_event)
            report = await report_service(
                session,
                period=period,
                **filter_kwargs,
                page=page,
                limit=batch_size,
            )
            if total is None:
                total = report.pagination.total
            batch_rows = list(report_csv_rows(report_type, report))
            if not batch_rows:
                break
            writer.writerows(
                [_safe_cell(value) for value in row]
                for row in batch_rows
            )
            written += len(batch_rows)
            page += 1
            if lease_lost_event is not None:
                _ensure_export_job_lease(lease_lost_event)
        return written


async def list_report_export_jobs(
    session: AsyncSession,
    *,
    requested_by: UUID,
    permissions: set[str],
) -> list[dict]:
    report_types = accessible_export_report_types(permissions)
    if not report_types:
        return []
    return await export_job_repo.list_export_jobs(
        session,
        requested_by=requested_by,
        report_types=report_types,
    )


async def cleanup_expired_report_exports() -> int:
    async with AsyncSessionFactory() as session:
        jobs = await export_job_repo.expire_due_export_jobs(session)
        await session.commit()
    export_root = EXPORT_DIRECTORY.resolve()
    removed = 0
    for job in jobs:
        file_path = job.get("filePath")
        if not file_path:
            continue
        resolved_path = Path(str(file_path)).resolve()
        if not resolved_path.is_relative_to(export_root):
            logger.warning(
                "report_export_cleanup_path_rejected",
                extra={
                    "event": "report_export_cleanup_path_rejected",
                    "job_id": job.get("id"),
                },
            )
            continue
        if resolved_path.exists():
            resolved_path.unlink()
            removed += 1
    orphaned_files = cleanup_orphaned_report_export_files()
    if jobs or orphaned_files:
        logger.info(
            "report_export_cleanup_completed",
            extra={
                "event": "report_export_cleanup_completed",
                "expired_jobs": len(jobs),
                "removed_files": removed,
                "removed_orphaned_files": orphaned_files,
            },
        )
    return len(jobs)


async def download_report_export(
    session: AsyncSession,
    *,
    job_id: UUID,
    requested_by: UUID,
    permissions: set[str],
) -> FileResponse:
    job = await export_job_repo.get_export_job(
        session,
        job_id=job_id,
        requested_by=requested_by,
    )
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy tác vụ xuất báo cáo.")
    ensure_report_type_access(job["reportType"], permissions)
    if job["status"] == "EXPIRED":
        raise HTTPException(status_code=410, detail="Tệp báo cáo đã hết hạn.")
    if job["status"] != "COMPLETED":
        raise HTTPException(status_code=409, detail="Báo cáo chưa sẵn sàng để tải.")
    if not job["expiresAt"] or job["expiresAt"] <= datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Tệp báo cáo đã hết hạn.")
    export_path = Path(job["filePath"]).resolve()
    try:
        export_path.relative_to(EXPORT_DIRECTORY.resolve())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đường dẫn tệp báo cáo không hợp lệ.",
        ) from exc
    if not export_path.is_file():
        raise HTTPException(status_code=410, detail="Tệp báo cáo không còn tồn tại.")
    return FileResponse(
        export_path,
        media_type="text/csv; charset=utf-8",
        filename=job["filename"],
    )
