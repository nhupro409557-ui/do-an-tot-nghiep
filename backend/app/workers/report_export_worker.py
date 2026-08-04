import asyncio
import logging
from time import monotonic

from app.application.reporting.export_job_service import (
    EXPORT_MAX_ATTEMPTS,
    cleanup_expired_report_exports,
    process_claimed_report_export_job,
)
from app.infrastructure.database.repositories.reporting import (
    export_jobs as export_job_repo,
)
from app.infrastructure.database.session import AsyncSessionFactory


POLL_INTERVAL_SECONDS = 2
STALE_AFTER_MINUTES = 15
CLEANUP_INTERVAL_SECONDS = 300
logger = logging.getLogger("ecommerce_app.reporting.worker")


async def run_report_export_worker_iteration() -> bool:
    async with AsyncSessionFactory() as session:
        job = await export_job_repo.claim_next_export_job(
            session,
            max_attempts=EXPORT_MAX_ATTEMPTS,
            stale_after_minutes=STALE_AFTER_MINUTES,
        )
        await session.commit()
    if not job:
        return False
    await process_claimed_report_export_job(job)
    return True


async def run_report_export_worker_loop() -> None:
    logger.info(
        "report_export_worker_started",
        extra={"event": "report_export_worker_started"},
    )
    next_cleanup_at = 0.0
    while True:
        try:
            if monotonic() >= next_cleanup_at:
                await cleanup_expired_report_exports()
                next_cleanup_at = monotonic() + CLEANUP_INTERVAL_SECONDS
            processed = await run_report_export_worker_iteration()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error(
                "report_export_worker_iteration_failed",
                extra={"event": "report_export_worker_iteration_failed"},
                exc_info=True,
            )
            processed = False
        if not processed:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
