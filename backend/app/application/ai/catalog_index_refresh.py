from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg

from app.application.ai.catalog_embedding_index import normalize_asyncpg_dsn
from app.config import settings


BACKEND_DIR = Path(__file__).resolve().parents[3]
OUTPUT_TAIL_CHARS = 4000
REFRESH_JOB_TABLE = "ai_catalog_index_jobs"

_refresh_lock = asyncio.Lock()
_refresh_job: dict | None = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _job_table_ddl() -> str:
    return f"""
    CREATE TABLE IF NOT EXISTS {REFRESH_JOB_TABLE} (
        id UUID PRIMARY KEY,
        status TEXT NOT NULL,
        step TEXT NOT NULL,
        started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        finished_at TIMESTAMPTZ,
        output_tail TEXT NOT NULL DEFAULT '',
        error TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT ai_catalog_index_jobs_status_check
            CHECK (status IN ('queued', 'running', 'succeeded', 'failed'))
    )
    """


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(normalize_asyncpg_dsn(settings.database_url))


async def _ensure_job_table(connection: asyncpg.Connection) -> None:
    await connection.execute(_job_table_ddl())


async def _persist_refresh_job(job: dict) -> None:
    connection = await _connect()
    try:
        await _ensure_job_table(connection)
        await connection.execute(
            f"""
            INSERT INTO {REFRESH_JOB_TABLE} (
                id,
                status,
                step,
                started_at,
                finished_at,
                output_tail,
                error,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                step = EXCLUDED.step,
                started_at = EXCLUDED.started_at,
                finished_at = EXCLUDED.finished_at,
                output_tail = EXCLUDED.output_tail,
                error = EXCLUDED.error,
                updated_at = NOW()
            """,
            UUID(job["id"]),
            job["status"],
            job["step"],
            _parse_iso(job.get("started_at")),
            _parse_iso(job.get("finished_at")),
            job.get("output_tail") or "",
            job.get("error"),
        )
    finally:
        await connection.close()


async def _persist_refresh_job_safely(job: dict) -> None:
    try:
        await _persist_refresh_job(job)
    except (OSError, asyncpg.PostgresError) as exc:
        job["persistence_error"] = str(exc)


def _row_to_job(row) -> dict:
    return {
        "id": str(row["id"]),
        "status": row["status"],
        "step": row["step"],
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "finished_at": row["finished_at"].isoformat() if row["finished_at"] else None,
        "output_tail": row["output_tail"],
        "error": row["error"],
    }


async def list_recent_refresh_jobs(limit: int = 10) -> list[dict]:
    connection = await _connect()
    try:
        await _ensure_job_table(connection)
        rows = await connection.fetch(
            f"""
            SELECT id, status, step, started_at, finished_at, output_tail, error
            FROM {REFRESH_JOB_TABLE}
            ORDER BY started_at DESC
            LIMIT $1
            """,
            max(1, min(limit, 50)),
        )
        return [_row_to_job(row) for row in rows]
    finally:
        await connection.close()


def _cocoindex_command() -> list[str]:
    executable = (
        BACKEND_DIR / ".venv" / "Scripts" / "cocoindex.exe"
        if os.name == "nt"
        else BACKEND_DIR / ".venv" / "bin" / "cocoindex"
    )
    return [str(executable if executable.exists() else "cocoindex")]


def _command_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("COCOINDEX_DB", str(BACKEND_DIR / "var" / "cocoindex" / "cocoindex.db"))
    return env


def current_refresh_job() -> dict | None:
    return dict(_refresh_job) if _refresh_job else None


async def start_refresh_job() -> dict:
    global _refresh_job
    if _refresh_lock.locked() or (_refresh_job and _refresh_job.get("status") in {"queued", "running"}):
        return {
            "started": False,
            "reason": "AI catalog index refresh is already running.",
            "job": current_refresh_job(),
        }

    _refresh_job = {
        "id": str(uuid4()),
        "status": "queued",
        "step": "queued",
        "started_at": _now_iso(),
        "finished_at": None,
        "output_tail": "",
        "error": None,
    }
    await _persist_refresh_job_safely(_refresh_job)
    asyncio.create_task(run_refresh_job())
    return {
        "started": True,
        "job": current_refresh_job(),
    }


async def _run_command(step: str, command: list[str]) -> None:
    assert _refresh_job is not None
    _refresh_job["step"] = step
    await _persist_refresh_job_safely(_refresh_job)
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(BACKEND_DIR),
        env=_command_env(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output_bytes, _ = await process.communicate()
    output = output_bytes.decode("utf-8", errors="replace")
    combined = (_refresh_job.get("output_tail") or "") + "\n" + output
    _refresh_job["output_tail"] = combined[-OUTPUT_TAIL_CHARS:]
    await _persist_refresh_job_safely(_refresh_job)
    if process.returncode != 0:
        raise RuntimeError(f"{step} failed with exit code {process.returncode}.")


async def run_refresh_job() -> None:
    assert _refresh_job is not None
    async with _refresh_lock:
        try:
            _refresh_job["status"] = "running"
            await _persist_refresh_job_safely(_refresh_job)
            await _run_command("migrations", [sys.executable, "scripts/run_migrations.py"])
            await _run_command(
                "cocoindex_markdown",
                [*_cocoindex_command(), "update", str(Path("app") / "application" / "ai" / "cocoindex_catalog.py")],
            )
            await _run_command(
                "embedding_sync",
                [sys.executable, "-m", "app.application.ai.catalog_embedding_index"],
            )
            _refresh_job["status"] = "succeeded"
            _refresh_job["step"] = "done"
        except Exception as exc:
            _refresh_job["status"] = "failed"
            _refresh_job["error"] = str(exc)
        finally:
            _refresh_job["finished_at"] = _now_iso()
            await _persist_refresh_job_safely(_refresh_job)
