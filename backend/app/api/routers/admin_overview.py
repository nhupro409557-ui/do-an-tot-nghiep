from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_user_permissions, require_permission
from app.application.services.overview_service import get_admin_overview
from app.infrastructure.database.session import get_session


router = APIRouter()


@router.get("/overview", dependencies=[Depends(require_permission("overview:read"))])
async def overview(
    session: AsyncSession = Depends(get_session),
    permissions: set[str] = Depends(get_user_permissions),
) -> dict:
    result = await get_admin_overview(session)
    if "report:profit_read" not in permissions:
        result.pop("costOfGoodsSold", None)
        result.pop("grossProfit", None)
    return result
