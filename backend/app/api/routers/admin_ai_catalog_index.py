from fastapi import APIRouter, Depends

from app.api.dependencies import require_admin
from app.application.ai.catalog_index_refresh import (
    current_refresh_job,
    list_recent_refresh_jobs,
    start_refresh_job,
)
from app.application.ai.catalog_index_status import collect_status


router = APIRouter()


@router.get("/ai-catalog-index/status", dependencies=[Depends(require_admin)])
async def get_ai_catalog_index_status() -> dict:
    status = await collect_status()
    status["refresh_job"] = current_refresh_job()
    status["recent_refresh_jobs"] = await list_recent_refresh_jobs(limit=5)
    return status


@router.post("/ai-catalog-index/refresh", dependencies=[Depends(require_admin)])
async def refresh_ai_catalog_index() -> dict:
    return await start_refresh_job()


@router.get("/ai-catalog-index/jobs", dependencies=[Depends(require_admin)])
async def list_ai_catalog_index_jobs(limit: int = 10) -> dict:
    return {
        "items": await list_recent_refresh_jobs(limit=limit),
    }
