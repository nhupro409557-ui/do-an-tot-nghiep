from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def insert_security_audit_log(
    session: AsyncSession,
    *,
    user_id,
    event_type: str,
    ip_address: str,
    user_agent: str | None,
    metadata_json: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs
                (user_id, event_type, ip_address, user_agent, metadata)
            VALUES
                (:user_id, :event_type, :ip_address, :user_agent, CAST(:metadata AS jsonb))
            """
        ),
        {
            "user_id": user_id,
            "event_type": event_type,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": metadata_json,
        },
    )


async def list_audit_logs(session: AsyncSession, *, filters: list[str], params: dict[str, object]) -> list[dict]:
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
