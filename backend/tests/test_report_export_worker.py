import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.application.reporting.export_job_service import (
    ReportExportLeaseLost,
    _maintain_export_job_lease,
    cleanup_orphaned_report_export_files,
    create_report_export_job,
    process_claimed_report_export_job,
    write_report_export_file,
)
from app.infrastructure.database.repositories.reporting.export_jobs import (
    mark_completed,
    refresh_export_job_heartbeat,
    retry_or_fail_export_job,
)
from app.workers.report_export_worker import run_report_export_worker_iteration


class _SessionContext:
    def __init__(self) -> None:
        self.session = AsyncMock()

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_args):
        return None


class _ScalarResult:
    def __init__(self, value=None) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class ReportExportWorkerTest(unittest.IsolatedAsyncioTestCase):
    def test_lease_migration_enforces_processing_state_invariant(self) -> None:
        migration_path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "102_report_export_job_lease.sql"
        )
        migration_sql = " ".join(
            migration_path.read_text(encoding="utf-8").split()
        )

        self.assertIn("report_export_jobs_lease_state_check", migration_sql)
        self.assertIn(
            "status = 'PROCESSING' AND claim_token IS NOT NULL "
            "AND heartbeat_at IS NOT NULL",
            migration_sql,
        )
        self.assertIn(
            "status <> 'PROCESSING' AND claim_token IS NULL "
            "AND heartbeat_at IS NULL",
            migration_sql,
        )

    async def test_stale_owner_cannot_mark_job_completed(self) -> None:
        session = AsyncMock()
        session.execute.return_value = _ScalarResult()

        updated = await mark_completed(
            session,
            job_id=uuid4(),
            claim_token=uuid4(),
            total_rows=10,
            file_path="C:/exports/report.csv",
            filename="report.csv",
            expires_at=datetime.now(timezone.utc),
        )

        self.assertFalse(updated)

    async def test_stale_owner_cannot_retry_job(self) -> None:
        session = AsyncMock()
        session.execute.return_value = _ScalarResult()

        next_status = await retry_or_fail_export_job(
            session,
            job_id=uuid4(),
            claim_token=uuid4(),
            max_attempts=3,
            retry_delay_seconds=30,
        )

        self.assertIsNone(next_status)

    async def test_heartbeat_reports_lost_lease(self) -> None:
        session = AsyncMock()
        session.execute.return_value = _ScalarResult()

        refreshed = await refresh_export_job_heartbeat(
            session,
            job_id=uuid4(),
            claim_token=uuid4(),
        )

        self.assertFalse(refreshed)

    async def test_heartbeat_loop_stops_when_token_is_no_longer_owner(self) -> None:
        context = _SessionContext()
        stop_event = asyncio.Event()
        lease_lost_event = asyncio.Event()

        with (
            patch(
                "app.application.reporting.export_job_service.AsyncSessionFactory",
                new=lambda: context,
            ),
            patch(
                "app.application.reporting.export_job_service."
                "EXPORT_HEARTBEAT_INTERVAL_SECONDS",
                new=0.001,
            ),
            patch(
                "app.application.reporting.export_job_service."
                "export_job_repo.refresh_export_job_heartbeat",
                new=AsyncMock(return_value=False),
            ),
        ):
            await asyncio.wait_for(
                _maintain_export_job_lease(
                    job_id=uuid4(),
                    claim_token=uuid4(),
                    stop_event=stop_event,
                    lease_lost_event=lease_lost_event,
                ),
                timeout=1,
            )

        self.assertTrue(lease_lost_event.is_set())
        context.session.commit.assert_awaited_once()

    async def test_writer_stops_before_query_when_lease_is_lost(self) -> None:
        lease_lost = asyncio.Event()
        lease_lost.set()

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ReportExportLeaseLost):
                await write_report_export_file(
                    AsyncMock(),
                    "revenue",
                    {
                        "from": "2026-07-01",
                        "to": "2026-08-01",
                    },
                    Path(directory) / "revenue.csv",
                    lease_lost_event=lease_lost,
                )

    async def test_lost_owner_does_not_leave_a_published_file(self) -> None:
        context = _SessionContext()
        job_id = uuid4()
        claim_token = uuid4()

        async def write_temporary_file(*_args, **_kwargs) -> int:
            path = Path(_args[3])
            path.write_text("header\n", encoding="utf-8")
            return 1

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch(
                    "app.application.reporting.export_job_service.AsyncSessionFactory",
                    new=lambda: context,
                ),
                patch(
                    "app.application.reporting.export_job_service.EXPORT_DIRECTORY",
                    new=Path(directory),
                ),
                patch(
                    "app.application.reporting.export_job_service."
                    "write_report_export_file",
                    new=AsyncMock(side_effect=write_temporary_file),
                ),
                patch(
                    "app.application.reporting.export_job_service."
                    "export_job_repo.mark_completed",
                    new=AsyncMock(return_value=False),
                ),
            ):
                await process_claimed_report_export_job(
                    {
                        "id": str(job_id),
                        "claimToken": str(claim_token),
                        "reportType": "orders",
                        "filters": {
                            "from": "2026-07-01",
                            "to": "2026-08-01",
                        },
                        "attemptCount": 1,
                    }
                )

            self.assertEqual(list(Path(directory).iterdir()), [])

    async def test_uncertain_commit_keeps_published_file_for_reconciliation(self) -> None:
        context = _SessionContext()
        context.session.commit.side_effect = [
            RuntimeError("Không xác định được kết quả commit."),
            None,
        ]
        job_id = uuid4()
        claim_token = uuid4()

        async def write_temporary_file(*_args, **_kwargs) -> int:
            path = Path(_args[3])
            path.write_text("header\n", encoding="utf-8")
            return 1

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch(
                    "app.application.reporting.export_job_service.AsyncSessionFactory",
                    new=lambda: context,
                ),
                patch(
                    "app.application.reporting.export_job_service.EXPORT_DIRECTORY",
                    new=Path(directory),
                ),
                patch(
                    "app.application.reporting.export_job_service."
                    "write_report_export_file",
                    new=AsyncMock(side_effect=write_temporary_file),
                ),
                patch(
                    "app.application.reporting.export_job_service."
                    "export_job_repo.mark_completed",
                    new=AsyncMock(return_value=True),
                ),
                patch(
                    "app.application.reporting.export_job_service."
                    "export_job_repo.retry_or_fail_export_job",
                    new=AsyncMock(return_value=None),
                ),
            ):
                await process_claimed_report_export_job(
                    {
                        "id": str(job_id),
                        "claimToken": str(claim_token),
                        "reportType": "orders",
                        "filters": {
                            "from": "2026-07-01",
                            "to": "2026-08-01",
                        },
                        "attemptCount": 1,
                    }
                )

            files = list(Path(directory).iterdir())
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].suffix, ".csv")

    def test_cleanup_removes_only_old_tokenized_report_files(self) -> None:
        job_id = uuid4()
        claim_token = uuid4()

        with tempfile.TemporaryDirectory() as directory:
            export_directory = Path(directory)
            orphan_path = (
                export_directory / f"orders-{job_id}-{claim_token}.csv"
            )
            recent_path = (
                export_directory / f"customers-{uuid4()}-{uuid4()}.csv"
            )
            unrelated_path = export_directory / "bao-cao-thu-cong.csv"
            for path in (orphan_path, recent_path, unrelated_path):
                path.write_text("header\n", encoding="utf-8")

            old_timestamp = (
                datetime.now(timezone.utc) - timedelta(hours=26)
            ).timestamp()
            os.utime(orphan_path, (old_timestamp, old_timestamp))
            os.utime(unrelated_path, (old_timestamp, old_timestamp))

            with patch(
                "app.application.reporting.export_job_service.EXPORT_DIRECTORY",
                new=export_directory,
            ):
                removed = cleanup_orphaned_report_export_files()

            self.assertEqual(removed, 1)
            self.assertFalse(orphan_path.exists())
            self.assertTrue(recent_path.exists())
            self.assertTrue(unrelated_path.exists())

    async def test_create_rejects_more_than_three_active_jobs_per_user(self) -> None:
        session = AsyncMock()
        with (
            patch(
                "app.application.reporting.export_job_service."
                "export_job_repo.lock_export_queue_for_user",
                new=AsyncMock(),
            ),
            patch(
                "app.application.reporting.export_job_service."
                "export_job_repo.count_active_export_jobs",
                new=AsyncMock(return_value=3),
            ),
            patch(
                "app.application.reporting.export_job_service."
                "export_job_repo.create_export_job",
                new=AsyncMock(),
            ) as create,
        ):
            with self.assertRaises(HTTPException) as context:
                await create_report_export_job(
                    session,
                    requested_by=uuid4(),
                    report_type="orders",
                    filters={"from": "2026-07-01", "to": "2026-08-01"},
                )

        self.assertEqual(context.exception.status_code, 429)
        session.rollback.assert_awaited_once()
        create.assert_not_awaited()

    async def test_iteration_claims_then_dispatches_one_job(self) -> None:
        context = _SessionContext()
        job = {
            "id": str(uuid4()),
            "reportType": "orders",
            "filters": {"from": "2026-07-01", "to": "2026-08-01"},
            "attemptCount": 1,
        }
        with (
            patch(
                "app.workers.report_export_worker.AsyncSessionFactory",
                new=lambda: context,
            ),
            patch(
                "app.workers.report_export_worker."
                "export_job_repo.claim_next_export_job",
                new=AsyncMock(return_value=job),
            ) as claim,
            patch(
                "app.workers.report_export_worker."
                "process_claimed_report_export_job",
                new=AsyncMock(),
            ) as process,
        ):
            processed = await run_report_export_worker_iteration()

        self.assertTrue(processed)
        claim.assert_awaited_once()
        context.session.commit.assert_awaited_once()
        process.assert_awaited_once_with(job)

    async def test_iteration_idles_when_queue_is_empty(self) -> None:
        context = _SessionContext()
        with (
            patch(
                "app.workers.report_export_worker.AsyncSessionFactory",
                new=lambda: context,
            ),
            patch(
                "app.workers.report_export_worker."
                "export_job_repo.claim_next_export_job",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "app.workers.report_export_worker."
                "process_claimed_report_export_job",
                new=AsyncMock(),
            ) as process,
        ):
            processed = await run_report_export_worker_iteration()

        self.assertFalse(processed)
        process.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
