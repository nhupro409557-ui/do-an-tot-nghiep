from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_permission
from app.api.v1.schemas.admin import ReviewStatusPayload
from app.application.services import review_service
from app.infrastructure.database.session import get_session

router = APIRouter()


@router.get("/reviews", dependencies=[Depends(require_permission("review:read"))])
async def list_admin_reviews(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await review_service.list_admin_reviews(session)


@router.get("/reviews/summary", dependencies=[Depends(require_permission("review:read"))])
async def list_admin_review_summary(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await review_service.list_admin_review_summary(session)


@router.patch("/reviews/{review_id}", dependencies=[Depends(require_permission("review:update"))])
async def update_review_status(review_id: UUID, payload: ReviewStatusPayload, session: AsyncSession = Depends(get_session)) -> dict:
    return await review_service.update_review_status(session, review_id, payload)


@router.delete("/reviews/{review_id}", dependencies=[Depends(require_permission("review:delete"))])
async def delete_review(review_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await review_service.delete_review(session, review_id)
