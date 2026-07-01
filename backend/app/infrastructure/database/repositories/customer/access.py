from .common import *

async def revoke_user_sessions(session: AsyncSession, *, user_id: UUID, reason: str) -> None:
    await session.execute(
        text("UPDATE refresh_token_sessions SET revoked_at = NOW() WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    await session.execute(
        text(
            """
            INSERT INTO auth_session_revocations (user_id, revoked_after, reason)
            VALUES (:user_id, NOW(), :reason)
            ON CONFLICT (user_id)
            DO UPDATE SET revoked_after = EXCLUDED.revoked_after, reason = EXCLUDED.reason, created_at = NOW()
            """
        ),
        {"user_id": user_id, "reason": reason},
    )


async def get_active_user_id_by_email(session: AsyncSession, email: str) -> UUID | None:
    return await session.scalar(text("SELECT id FROM users WHERE LOWER(email) = :email AND status != 'DELETED'"), {"email": email})


async def get_role_id_by_code(session: AsyncSession, code: str) -> UUID | None:
    return await session.scalar(text("SELECT id FROM roles WHERE code = :code"), {"code": code})


async def insert_staff_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    role_id: UUID,
    email: str,
    password_hash: str,
    full_name: str,
    phone: str | None,
    status: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO users (
                id, role_id, email, password_hash, full_name, phone, status,
                marketing_opt_in, profile, addresses, loyalty_points_balance,
                loyalty_tier, loyalty_wallet_status, created_at, updated_at
            )
            VALUES (
                :id, :role_id, :email, :password_hash, :full_name, :phone, :status,
                FALSE, '{}'::jsonb, '[]'::jsonb, 0, 'MEMBER', 'ACTIVE', NOW(), NOW()
            )
            """
        ),
        {
            "id": user_id,
            "role_id": role_id,
            "email": email,
            "password_hash": password_hash,
            "full_name": full_name,
            "phone": phone,
            "status": status,
        },
    )


async def bulk_update_user_status(session: AsyncSession, *, user_ids: list[UUID], status: str) -> int:
    result = await session.execute(
        text(
            """
            UPDATE users
            SET status = :status, updated_at = NOW()
            WHERE id IN :user_ids AND status != 'DELETED'
            """
        ).bindparams(bindparam("user_ids", expanding=True)),
        {"status": status, "user_ids": user_ids},
    )
    return int(result.rowcount or 0)


async def get_user_role(session: AsyncSession, user_id: UUID) -> str | None:
    row = (
        await session.execute(
            text(
                """
                SELECT r.code AS role
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = :user_id AND u.status != 'DELETED'
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    return str(row["role"]) if row else None


async def get_user_access_for_update(session: AsyncSession, user_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT r.code AS role, u.status
                FROM users u
                JOIN roles r ON r.id = u.role_id
                WHERE u.id = :user_id AND u.status != 'DELETED'
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_user_role_and_status(session: AsyncSession, *, user_id: UUID, role_id: UUID, status: str) -> None:
    await session.execute(
        text(
            """
            UPDATE users
            SET role_id = :role_id, status = :status, updated_at = NOW()
            WHERE id = :user_id AND status != 'DELETED'
            """
        ),
        {"user_id": user_id, "role_id": role_id, "status": status},
    )


async def get_role(session: AsyncSession, role_id: UUID) -> dict | None:
    row = (
        await session.execute(text("SELECT id::text, code, name FROM roles WHERE id = :id"), {"id": role_id})
    ).mappings().first()
    return dict(row) if row else None


async def list_role_permission_codes(session: AsyncSession, role_id: UUID) -> list[str]:
    result = await session.execute(
        text(
            """
            SELECT p.code
            FROM role_permissions rp
            JOIN permissions p ON p.id = rp.permission_id
            WHERE rp.role_id = :role_id
            ORDER BY p.code
            """
        ),
        {"role_id": role_id},
    )
    return [str(code) for code in result.scalars().all()]


async def get_role_code(session: AsyncSession, role_id: UUID) -> str | None:
    return await session.scalar(text("SELECT code FROM roles WHERE id = :id"), {"id": role_id})


async def replace_role_permissions(session: AsyncSession, *, role_id: UUID, permission_codes: list[str]) -> None:
    await session.execute(text("DELETE FROM role_permissions WHERE role_id = :role_id"), {"role_id": role_id})
    if permission_codes:
        await session.execute(
            text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT :role_id, id
                FROM permissions
                WHERE code IN :codes
                ON CONFLICT DO NOTHING
                """
            ).bindparams(bindparam("codes", expanding=True)),
            {"role_id": role_id, "codes": list(permission_codes)},
        )


async def list_user_ids_by_role(session: AsyncSession, role_id: UUID) -> list[UUID]:
    result = await session.execute(text("SELECT id FROM users WHERE role_id = :role_id"), {"role_id": role_id})
    return list(result.scalars().all())
