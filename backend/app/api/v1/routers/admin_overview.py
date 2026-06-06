from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_permission
from app.application.services.overview_service import get_admin_overview
from app.infrastructure.database.session import get_session


router = APIRouter()


@router.get("/overview", dependencies=[Depends(require_permission("overview:read"))])
async def overview(session: AsyncSession = Depends(get_session)) -> dict:
    return await get_admin_overview(session)
