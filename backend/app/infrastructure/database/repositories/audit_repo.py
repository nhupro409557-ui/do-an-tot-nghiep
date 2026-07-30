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
            SELECT log.id::text, log.user_id::text AS "userId", log.event_type AS "eventType",
                   COALESCE(u.email, log.email) AS email,
                   u.full_name AS "actorName",
                   r.code AS "actorRole",
                   log.ip_address AS "ipAddress", log.user_agent AS "userAgent",
                   log.metadata, log.created_at AS "createdAt"
            FROM security_audit_logs log
            LEFT JOIN users u ON u.id = log.user_id
            LEFT JOIN roles r ON r.id = u.role_id
            WHERE {' AND '.join(filters)}
            ORDER BY log.created_at DESC
            LIMIT :limit
            """
        ),
        params,
    )
    return [dict(row._mapping) for row in result]
