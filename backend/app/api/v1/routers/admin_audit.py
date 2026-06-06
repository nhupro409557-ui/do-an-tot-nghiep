from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_permission
from app.infrastructure.database.session import get_session
from app.application.services import audit_service


router = APIRouter()


@router.get("/audit-logs", dependencies=[Depends(require_permission("audit:read"))])
async def list_audit_logs(
    event_type: str | None = None,
    actor_id: UUID | None = None,
    resource: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await audit_service.list_audit_logs(
        session,
        event_type=event_type,
        actor_id=actor_id,
        resource=resource,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )
