from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import audit_repo


async def list_audit_logs(
    session: AsyncSession,
    *,
    event_type: str | None = None,
    actor_id: UUID | None = None,
    resource: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 100,
) -> list[dict]:
    limit = max(1, min(limit, 500))
    filters = ["log.event_type LIKE 'admin_%'"]
    params: dict[str, object] = {"limit": limit}
    if event_type:
        filters.append("log.event_type = :event_type")
        params["event_type"] = event_type
    if actor_id:
        filters.append("log.user_id = :actor_id")
        params["actor_id"] = actor_id
    if resource:
        filters.append("log.metadata->>'resource' = :resource")
        params["resource"] = resource
    if from_date:
        filters.append("log.created_at >= CAST(:from_date AS timestamptz)")
        params["from_date"] = from_date
    if to_date:
        filters.append("log.created_at <= CAST(:to_date AS timestamptz)")
        params["to_date"] = to_date
    return await audit_repo.list_audit_logs(session, filters=filters, params=params)
