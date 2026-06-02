from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_permission
from app.infrastructure.database.session import get_session


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
    limit = max(1, min(limit, 500))
    filters = ["event_type LIKE 'admin_%'"]
    params: dict[str, object] = {"limit": limit}
    if event_type:
        filters.append("event_type = :event_type")
        params["event_type"] = event_type
    if actor_id:
        filters.append("user_id = :actor_id")
        params["actor_id"] = actor_id
    if resource:
        filters.append("metadata->>'resource' = :resource")
        params["resource"] = resource
    if from_date:
        filters.append("created_at >= CAST(:from_date AS timestamptz)")
        params["from_date"] = from_date
    if to_date:
        filters.append("created_at <= CAST(:to_date AS timestamptz)")
        params["to_date"] = to_date
    result = await session.execute(
        text(
            f"""
            SELECT id::text, user_id::text AS "userId", event_type AS "eventType",
                   email, ip_address AS "ipAddress", user_agent AS "userAgent",
                   metadata, created_at AS "createdAt"
            FROM security_audit_logs
            WHERE {' AND '.join(filters)}
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        params,
    )
    return [dict(row._mapping) for row in result]
