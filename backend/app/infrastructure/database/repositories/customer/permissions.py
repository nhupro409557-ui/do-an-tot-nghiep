from .common import *

async def list_permissions(session: AsyncSession) -> list[dict]:
    result = await session.execute(text("SELECT id::text, code, module, description FROM permissions ORDER BY module, code"))
    return [dict(row._mapping) for row in result]


async def list_roles(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id::text, code, name
            FROM roles
            WHERE code IN ('CUSTOMER', 'STAFF_ADMIN')
            ORDER BY CASE code WHEN 'STAFF_ADMIN' THEN 1 ELSE 2 END
            """
        )
    )
    return [dict(row._mapping) for row in result]


async def ensure_user_permissions_table(session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS user_permissions (
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
                granted_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (user_id, permission_id)
            )
            """
        )
    )
    await session.execute(text("CREATE INDEX IF NOT EXISTS idx_user_permissions_permission_id ON user_permissions(permission_id)"))


async def list_known_permission_codes(session: AsyncSession, codes: list[str]) -> list[str]:
    result = await session.execute(
        text("SELECT code FROM permissions WHERE code IN :codes").bindparams(bindparam("codes", expanding=True)),
        {"codes": codes},
    )
    return [str(code) for code in result.scalars().all()]


async def delete_user_extra_permissions(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(text("DELETE FROM user_permissions WHERE user_id = :user_id"), {"user_id": user_id})


async def insert_user_extra_permissions(session: AsyncSession, user_id: UUID, codes: list[str]) -> None:
    await session.execute(
        text(
            """
            INSERT INTO user_permissions (user_id, permission_id)
            SELECT :user_id, id
            FROM permissions
            WHERE code IN :codes
            ON CONFLICT DO NOTHING
            """
        ).bindparams(bindparam("codes", expanding=True)),
        {"user_id": user_id, "codes": codes},
    )


async def list_user_extra_permissions(session: AsyncSession, user_id: UUID) -> list[str]:
    result = await session.execute(
        text(
            """
            SELECT p.code
            FROM user_permissions up
            JOIN permissions p ON p.id = up.permission_id
            WHERE up.user_id = :user_id
            ORDER BY p.code
            """
        ),
        {"user_id": user_id},
    )
    return [str(code) for code in result.scalars().all()]


async def audit_admin_event(
    session: AsyncSession,
    *,
    actor_id: UUID,
    event_type: str,
    resource: str,
    target_user_id: UUID | None = None,
    metadata: dict | None = None,
) -> None:
    payload = {"resource": resource, **(metadata or {})}
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs (user_id, event_type, metadata)
            VALUES (:actor_id, :event_type, CAST(:metadata AS jsonb))
            """
        ),
        {
            "actor_id": actor_id,
            "event_type": event_type,
            "metadata": json.dumps(
                {
                    **payload,
                    **({"targetUserId": str(target_user_id)} if target_user_id else {}),
                },
                ensure_ascii=False,
            ),
        },
    )
