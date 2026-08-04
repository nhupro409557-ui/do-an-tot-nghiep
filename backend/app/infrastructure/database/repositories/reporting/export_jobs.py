import json
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def lock_export_queue_for_user(
    session: AsyncSession,
    requested_by: UUID,
) -> None:
    await session.execute(
        text(
            """
            SELECT pg_advisory_xact_lock(
                hashtextextended(CAST(:requested_by AS text), 0)
            )
            """
        ),
        {"requested_by": requested_by},
    )


async def count_active_export_jobs(
    session: AsyncSession,
    requested_by: UUID,
) -> int:
    result = await session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM report_export_jobs
            WHERE requested_by = :requested_by
              AND status IN ('PENDING', 'PROCESSING')
            """
        ),
        {"requested_by": requested_by},
    )
    return int(result.scalar_one() or 0)


async def create_export_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    requested_by: UUID,
    report_type: str,
    filters: dict,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO report_export_jobs (
                id, requested_by, report_type, status, filters
            )
            VALUES (
                :id, :requested_by, :report_type, 'PENDING',
                CAST(:filters AS jsonb)
            )
            """
        ),
        {
            "id": job_id,
            "requested_by": requested_by,
            "report_type": report_type,
            "filters": json.dumps(filters, ensure_ascii=False),
        },
    )


async def claim_next_export_job(
    session: AsyncSession,
    *,
    max_attempts: int,
    stale_after_minutes: int,
) -> dict | None:
    claim_token = uuid4()
    result = await session.execute(
        text(
            """
            WITH recovered AS (
                UPDATE report_export_jobs
                SET status = CASE
                        WHEN attempt_count >= :max_attempts THEN 'FAILED'
                        ELSE 'PENDING'
                    END,
                    error_message = CASE
                        WHEN attempt_count >= :max_attempts
                        THEN 'Tác vụ không thể phục hồi sau nhiều lần thử.'
                        ELSE error_message
                    END,
                    claimed_at = NULL,
                    claim_token = NULL,
                    heartbeat_at = NULL,
                    next_attempt_at = CASE
                        WHEN attempt_count >= :max_attempts THEN NULL
                        ELSE NOW()
                    END,
                    updated_at = NOW()
                WHERE status = 'PROCESSING'
                  AND COALESCE(heartbeat_at, claimed_at, updated_at)
                      < NOW() - make_interval(mins => :stale_after_minutes)
            ),
            candidate AS (
                SELECT id
                FROM report_export_jobs
                WHERE status = 'PENDING'
                  AND attempt_count < :max_attempts
                  AND (next_attempt_at IS NULL OR next_attempt_at <= NOW())
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE report_export_jobs jobs
            SET status = 'PROCESSING',
                attempt_count = jobs.attempt_count + 1,
                claimed_at = NOW(),
                claim_token = :claim_token,
                heartbeat_at = NOW(),
                error_message = NULL,
                updated_at = NOW()
            FROM candidate
            WHERE jobs.id = candidate.id
            RETURNING
                jobs.id::text,
                jobs.report_type AS "reportType",
                jobs.filters,
                jobs.attempt_count AS "attemptCount",
                jobs.claim_token::text AS "claimToken"
            """
        ),
        {
            "max_attempts": max_attempts,
            "stale_after_minutes": stale_after_minutes,
            "claim_token": claim_token,
        },
    )
    row = result.mappings().one_or_none()
    return dict(row) if row else None


async def mark_completed(
    session: AsyncSession,
    *,
    job_id: UUID,
    claim_token: UUID,
    total_rows: int,
    file_path: str,
    filename: str,
    expires_at: datetime,
) -> bool:
    result = await session.execute(
        text(
            """
            UPDATE report_export_jobs
            SET status = 'COMPLETED',
                total_rows = :total_rows,
                file_path = :file_path,
                filename = :filename,
                expires_at = :expires_at,
                claimed_at = NULL,
                claim_token = NULL,
                heartbeat_at = NULL,
                next_attempt_at = NULL,
                error_message = NULL,
                updated_at = NOW()
            WHERE id = :id
              AND status = 'PROCESSING'
              AND claim_token = :claim_token
            RETURNING id
            """
        ),
        {
            "id": job_id,
            "claim_token": claim_token,
            "total_rows": total_rows,
            "file_path": file_path,
            "filename": filename,
            "expires_at": expires_at,
        },
    )
    return result.scalar_one_or_none() is not None


async def refresh_export_job_heartbeat(
    session: AsyncSession,
    *,
    job_id: UUID,
    claim_token: UUID,
) -> bool:
    result = await session.execute(
        text(
            """
            UPDATE report_export_jobs
            SET heartbeat_at = NOW(),
                updated_at = NOW()
            WHERE id = :id
              AND status = 'PROCESSING'
              AND claim_token = :claim_token
            RETURNING id
            """
        ),
        {"id": job_id, "claim_token": claim_token},
    )
    return result.scalar_one_or_none() is not None


async def retry_or_fail_export_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    claim_token: UUID,
    max_attempts: int,
    retry_delay_seconds: int,
) -> str | None:
    result = await session.execute(
        text(
            """
            UPDATE report_export_jobs
            SET status = CASE
                    WHEN attempt_count >= :max_attempts THEN 'FAILED'
                    ELSE 'PENDING'
                END,
                error_message = CASE
                    WHEN attempt_count >= :max_attempts
                    THEN 'Không thể xuất báo cáo sau nhiều lần thử.'
                    ELSE NULL
                END,
                claimed_at = NULL,
                claim_token = NULL,
                heartbeat_at = NULL,
                next_attempt_at = CASE
                    WHEN attempt_count >= :max_attempts THEN NULL
                    ELSE NOW() + make_interval(secs => :retry_delay_seconds)
                END,
                updated_at = NOW()
            WHERE id = :id
              AND status = 'PROCESSING'
              AND claim_token = :claim_token
            RETURNING status
            """
        ),
        {
            "id": job_id,
            "claim_token": claim_token,
            "max_attempts": max_attempts,
            "retry_delay_seconds": retry_delay_seconds,
        },
    )
    next_status = result.scalar_one_or_none()
    return str(next_status) if next_status is not None else None


async def expire_due_export_jobs(
    session: AsyncSession,
    *,
    limit: int = 100,
) -> list[dict]:
    result = await session.execute(
        text(
            """
            WITH due AS (
                SELECT id, file_path
                FROM report_export_jobs
                WHERE status = 'COMPLETED'
                  AND expires_at <= NOW()
                ORDER BY expires_at
                FOR UPDATE SKIP LOCKED
                LIMIT :limit
            )
            UPDATE report_export_jobs jobs
            SET status = 'EXPIRED',
                file_path = NULL,
                updated_at = NOW()
            FROM due
            WHERE jobs.id = due.id
            RETURNING jobs.id::text, due.file_path AS "filePath"
            """
        ),
        {"limit": limit},
    )
    return [dict(row) for row in result.mappings().all()]


async def list_export_jobs(
    session: AsyncSession,
    *,
    requested_by: UUID,
    report_types: list[str],
) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                report_type AS "reportType",
                status,
                filters,
                total_rows AS "totalRows",
                filename,
                expires_at AS "expiresAt",
                error_message AS "errorMessage",
                created_at AS "createdAt",
                updated_at AS "updatedAt"
            FROM report_export_jobs
            WHERE requested_by = :requested_by
              AND report_type = ANY(CAST(:report_types AS text[]))
            ORDER BY created_at DESC
            LIMIT 20
            """
        ),
        {
            "requested_by": requested_by,
            "report_types": report_types,
        },
    )
    return [dict(row) for row in result.mappings().all()]


async def get_export_job(
    session: AsyncSession,
    *,
    job_id: UUID,
    requested_by: UUID,
) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                report_type AS "reportType",
                status,
                total_rows AS "totalRows",
                file_path AS "filePath",
                filename,
                expires_at AS "expiresAt",
                error_message AS "errorMessage"
            FROM report_export_jobs
            WHERE id = :id AND requested_by = :requested_by
            """
        ),
        {"id": job_id, "requested_by": requested_by},
    )
    row = result.mappings().one_or_none()
    return dict(row) if row else None
