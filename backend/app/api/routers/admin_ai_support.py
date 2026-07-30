from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_id, require_permission
from app.infrastructure.database.repositories import ai_repo
from app.infrastructure.database.session import get_session


router = APIRouter(
    prefix="/ai-support-requests",
    tags=["Admin - Hỗ trợ chatbot"],
    dependencies=[Depends(require_permission("after_sales:read"))],
)


class UpdateAISupportRequest(BaseModel):
    status: str = Field(pattern="^(OPEN|IN_PROGRESS|WAITING_CUSTOMER|RESOLVED|CLOSED)$")
    resolutionNote: str | None = Field(default=None, max_length=2000)


@router.get("")
async def list_ai_support_requests(
    status_value: str | None = Query(default=None, alias="status", pattern="^(OPEN|IN_PROGRESS|WAITING_CUSTOMER|RESOLVED|CLOSED)$"),
    limit: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await ai_repo.list_support_requests_for_admin(
        session,
        status_value=status_value,
        limit=limit,
    )


@router.patch("/{request_id}", dependencies=[Depends(require_permission("after_sales:update"))])
async def update_ai_support_request(
    request_id: UUID,
    payload: UpdateAISupportRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    updated = await ai_repo.update_support_request_for_admin(
        session,
        request_id=request_id,
        status_value=payload.status,
        resolution_note=payload.resolutionNote.strip() if payload.resolutionNote else None,
        assigned_to=current_user_id,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phiếu hỗ trợ chatbot.")
    await session.commit()
    return updated
