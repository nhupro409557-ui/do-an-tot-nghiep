import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Role, User


async def cleanup_expired_auth_tokens(session: AsyncSession) -> None:
    await session.execute(text("DELETE FROM registration_verification_tokens WHERE expires_at < NOW()"))
    await session.execute(text("DELETE FROM password_reset_tokens WHERE expires_at < NOW()"))


async def ensure_auth_verification_tables(session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS registration_verification_tokens (
                token TEXT PRIMARY KEY,
                code VARCHAR(6) NOT NULL,
                email VARCHAR(255) NOT NULL,
                password_hash TEXT NOT NULL,
                display_name VARCHAR(255) NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    await cleanup_expired_auth_tokens(session)


async def ensure_session_security_tables(session: AsyncSession) -> None:
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('emv_auth_security_tables'))"))
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS refresh_token_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                family_id UUID NOT NULL,
                user_agent TEXT,
                ip_address VARCHAR(80),
                expires_at TIMESTAMPTZ NOT NULL,
                revoked_at TIMESTAMPTZ,
                replaced_by UUID,
                grace_until TIMESTAMPTZ,
                replaced_by_token_hash TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                rotated_at TIMESTAMPTZ
            )
            """
        )
    )
    await session.execute(text("ALTER TABLE refresh_token_sessions ADD COLUMN IF NOT EXISTS grace_until TIMESTAMPTZ"))
    await session.execute(text("ALTER TABLE refresh_token_sessions ADD COLUMN IF NOT EXISTS replaced_by_token_hash TEXT"))
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS security_audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                event_type VARCHAR(80) NOT NULL,
                email VARCHAR(255),
                ip_address VARCHAR(80),
                user_agent TEXT,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS auth_session_revocations (
                user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                revoked_after TIMESTAMPTZ NOT NULL,
                reason VARCHAR(120) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    await session.execute(text("DELETE FROM refresh_token_sessions WHERE expires_at < NOW()"))


async def ensure_auth_session_revocation_table(session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS auth_session_revocations (
                user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                revoked_after TIMESTAMPTZ NOT NULL,
                reason VARCHAR(120) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )


async def get_session_revoked_after(session: AsyncSession, user_id: UUID):
    await ensure_auth_session_revocation_table(session)
    result = await session.execute(
        text(
            """
            SELECT revoked_after
            FROM auth_session_revocations
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    )
    return result.scalar_one_or_none()


async def ensure_admin_mfa_table(session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS admin_mfa_settings (
                user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                mfa_secret TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS admin_mfa_recovery_codes (
                user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                challenge_jti VARCHAR(64) NOT NULL,
                code_hash CHAR(64) NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                expires_at TIMESTAMPTZ NOT NULL,
                consumed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT ck_admin_mfa_recovery_attempt_count
                    CHECK (attempt_count >= 0 AND attempt_count <= 5)
            )
            """
        )
    )
    await session.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_admin_mfa_recovery_codes_expires_at "
            "ON admin_mfa_recovery_codes(expires_at)"
        )
    )


async def get_admin_mfa_row(session: AsyncSession, user_id: UUID) -> dict | None:
    await ensure_admin_mfa_table(session)
    row = (
        await session.execute(
            text("SELECT mfa_enabled, mfa_secret FROM admin_mfa_settings WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def upsert_admin_mfa_secret(session: AsyncSession, *, user_id: UUID, secret: str) -> None:
    await ensure_admin_mfa_table(session)
    await session.execute(
        text(
            """
            INSERT INTO admin_mfa_settings (user_id, mfa_enabled, mfa_secret)
            VALUES (:user_id, FALSE, :secret)
            ON CONFLICT (user_id)
            DO UPDATE SET
                mfa_enabled = FALSE,
                mfa_secret = EXCLUDED.mfa_secret,
                updated_at = NOW()
            """
        ),
        {"user_id": user_id, "secret": secret},
    )


async def enable_admin_mfa(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        text("UPDATE admin_mfa_settings SET mfa_enabled = TRUE, updated_at = NOW() WHERE user_id = :user_id"),
        {"user_id": user_id},
    )


async def replace_admin_mfa_recovery(
    session: AsyncSession,
    *,
    user_id: UUID,
    challenge_jti: str,
    code_hash: str,
    expires_at: datetime,
) -> None:
    await ensure_admin_mfa_table(session)
    await session.execute(
        text(
            """
            INSERT INTO admin_mfa_recovery_codes
                (user_id, challenge_jti, code_hash, attempt_count, expires_at, consumed_at)
            VALUES
                (:user_id, :challenge_jti, :code_hash, 0, :expires_at, NULL)
            ON CONFLICT (user_id)
            DO UPDATE SET
                challenge_jti = EXCLUDED.challenge_jti,
                code_hash = EXCLUDED.code_hash,
                attempt_count = 0,
                expires_at = EXCLUDED.expires_at,
                consumed_at = NULL,
                updated_at = NOW()
            """
        ),
        {
            "user_id": user_id,
            "challenge_jti": challenge_jti,
            "code_hash": code_hash,
            "expires_at": expires_at,
        },
    )


async def get_admin_mfa_recovery_for_update(session: AsyncSession, user_id: UUID) -> dict | None:
    await ensure_admin_mfa_table(session)
    row = (
        await session.execute(
            text(
                """
                SELECT challenge_jti, code_hash, attempt_count, expires_at, consumed_at
                FROM admin_mfa_recovery_codes
                WHERE user_id = :user_id
                FOR UPDATE
                """
            ),
            {"user_id": user_id},
        )
    ).mappings().one_or_none()
    return dict(row) if row else None


async def increment_admin_mfa_recovery_attempt(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE admin_mfa_recovery_codes
            SET attempt_count = LEAST(attempt_count + 1, 5), updated_at = NOW()
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    )


async def consume_admin_mfa_recovery(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE admin_mfa_recovery_codes
            SET consumed_at = NOW(), updated_at = NOW()
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    )


async def insert_security_audit_log(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    event_type: str,
    email: str | None,
    ip_address: str,
    user_agent: str | None,
    metadata: dict,
) -> None:
    await ensure_session_security_tables(session)
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs
                (user_id, event_type, email, ip_address, user_agent, metadata)
            VALUES
                (:user_id, :event_type, :email, :ip_address, :user_agent, CAST(:metadata AS jsonb))
            """
        ),
        {
            "user_id": user_id,
            "event_type": event_type,
            "email": email,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "metadata": json.dumps(metadata),
        },
    )


async def insert_refresh_session(
    session: AsyncSession,
    *,
    session_id: UUID,
    user_id: UUID,
    token_hash: str,
    family_id: UUID,
    user_agent: str | None,
    ip_address: str,
    expires_at: datetime,
) -> None:
    await ensure_session_security_tables(session)
    await session.execute(
        text(
            """
            UPDATE refresh_token_sessions
            SET revoked_at = NOW()
            WHERE user_id = :user_id
              AND revoked_at IS NULL
              AND expires_at > NOW()
              AND user_agent IS NOT DISTINCT FROM :user_agent
              AND ip_address IS NOT DISTINCT FROM :ip_address
            """
        ),
        {
            "user_id": user_id,
            "user_agent": user_agent,
            "ip_address": ip_address,
        },
    )
    await session.execute(
        text(
            """
            INSERT INTO refresh_token_sessions
                (id, user_id, token_hash, family_id, user_agent, ip_address, expires_at)
            VALUES
                (:id, :user_id, :token_hash, :family_id, :user_agent, :ip_address, :expires_at)
            """
        ),
        {
            "id": session_id,
            "user_id": user_id,
            "token_hash": token_hash,
            "family_id": family_id,
            "user_agent": user_agent,
            "ip_address": ip_address,
            "expires_at": expires_at,
        },
    )


async def get_valid_refresh_token_hash(session: AsyncSession, token_hash: str) -> str | None:
    result = await session.execute(
        text(
            """
            SELECT token_hash
            FROM refresh_token_sessions
            WHERE token_hash = :token_hash
              AND revoked_at IS NULL
              AND expires_at > NOW()
            """
        ),
        {"token_hash": token_hash},
    )
    return result.scalar_one_or_none()


async def get_refresh_session_for_update(session: AsyncSession, token_hash: str) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT id, user_id, family_id, expires_at, revoked_at, grace_until, user_agent, ip_address
            FROM refresh_token_sessions
            WHERE token_hash = :token_hash
            FOR UPDATE
            """
        ),
        {"token_hash": token_hash},
    )
    row = result.mappings().one_or_none()
    return dict(row) if row else None


async def get_refresh_session_id_by_hash(session: AsyncSession, token_hash: str) -> UUID:
    result = await session.execute(
        text("SELECT id FROM refresh_token_sessions WHERE token_hash = :token_hash"),
        {"token_hash": token_hash},
    )
    return result.scalar_one()


async def rotate_refresh_session(
    session: AsyncSession,
    *,
    old_session_id: UUID,
    new_session_id: UUID,
    new_token_hash: str,
    grace_seconds: int,
) -> None:
    await session.execute(
        text(
            """
            UPDATE refresh_token_sessions
            SET revoked_at = NOW(),
                rotated_at = NOW(),
                replaced_by = :new_id,
                replaced_by_token_hash = :new_hash,
                grace_until = NOW() + make_interval(secs => :grace_seconds)
            WHERE id = :old_id
            """
        ),
        {
            "new_id": new_session_id,
            "new_hash": new_token_hash,
            "grace_seconds": grace_seconds,
            "old_id": old_session_id,
        },
    )


async def revoke_refresh_session_by_hash(session: AsyncSession, token_hash: str) -> None:
    await session.execute(
        text("UPDATE refresh_token_sessions SET revoked_at = NOW() WHERE token_hash = :token_hash"),
        {"token_hash": token_hash},
    )


async def list_active_refresh_sessions(session: AsyncSession, user_id: UUID) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT id, token_hash, user_agent, ip_address, created_at, rotated_at, expires_at
            FROM refresh_token_sessions
            WHERE user_id = :user_id
              AND revoked_at IS NULL
              AND expires_at > NOW()
            ORDER BY created_at DESC
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row) for row in result.mappings()]


async def revoke_duplicate_active_refresh_sessions(session: AsyncSession, user_id: UUID) -> None:
    await ensure_session_security_tables(session)
    await session.execute(
        text(
            """
            WITH ranked_sessions AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_id, user_agent, ip_address
                        ORDER BY created_at DESC, id DESC
                    ) AS duplicate_rank
                FROM refresh_token_sessions
                WHERE user_id = :user_id
                  AND revoked_at IS NULL
                  AND expires_at > NOW()
            )
            UPDATE refresh_token_sessions
            SET revoked_at = NOW()
            WHERE id IN (
                SELECT id
                FROM ranked_sessions
                WHERE duplicate_rank > 1
            )
            """
        ),
        {"user_id": user_id},
    )


async def get_active_refresh_session_for_update(
    session: AsyncSession,
    *,
    session_id: UUID,
    user_id: UUID,
) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT id, token_hash
            FROM refresh_token_sessions
            WHERE id = :session_id
              AND user_id = :user_id
              AND revoked_at IS NULL
              AND expires_at > NOW()
            FOR UPDATE
            """
        ),
        {"session_id": session_id, "user_id": user_id},
    )
    row = result.mappings().one_or_none()
    return dict(row) if row else None


async def revoke_refresh_session_by_id(session: AsyncSession, session_id: UUID) -> None:
    await session.execute(
        text("UPDATE refresh_token_sessions SET revoked_at = NOW() WHERE id = :session_id"),
        {"session_id": session_id},
    )


async def revoke_all_user_refresh_sessions(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        text("UPDATE refresh_token_sessions SET revoked_at = NOW() WHERE user_id = :user_id"),
        {"user_id": user_id},
    )


async def upsert_auth_session_revocation(session: AsyncSession, *, user_id: UUID, reason: str) -> None:
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


async def get_role_code(session: AsyncSession, role_id: UUID) -> str | None:
    result = await session.execute(select(Role.code).where(Role.id == role_id))
    return result.scalar_one_or_none()


async def get_active_user_role_code(session: AsyncSession, user_id: UUID) -> str | None:
    result = await session.execute(
        text(
            """
            SELECT r.code
            FROM users u
            JOIN roles r ON r.id = u.role_id
            WHERE u.id = :user_id AND u.status = 'ACTIVE'
            """
        ),
        {"user_id": user_id},
    )
    return result.scalar_one_or_none()


async def get_customer_role_id(session: AsyncSession) -> UUID | None:
    result = await session.execute(select(Role.id).where(Role.code == "CUSTOMER"))
    return result.scalar_one_or_none()


async def add_customer_role(session: AsyncSession, *, role_id: UUID) -> None:
    session.add(Role(id=role_id, code="CUSTOMER", name="Customer"))
    await session.flush()


async def list_permissions_for_user(session: AsyncSession, user_id: UUID) -> list[str]:
    result = await session.execute(
        text(
            """
            SELECT DISTINCT code
            FROM (
                SELECT p.code
                FROM users u
                JOIN roles r ON r.id = u.role_id
                JOIN role_permissions rp ON rp.role_id = r.id
                JOIN permissions p ON p.id = rp.permission_id
                WHERE u.id = :user_id
                  AND u.status = 'ACTIVE'
                UNION
                SELECT p.code
                FROM users u
                JOIN user_permissions up ON up.user_id = u.id
                JOIN permissions p ON p.id = up.permission_id
                WHERE u.id = :user_id
                  AND u.status = 'ACTIVE'
            ) effective_permissions
            WHERE NOT EXISTS (
                SELECT 1 FROM user_permission_denials upd
                JOIN permissions denied ON denied.id = upd.permission_id
                WHERE upd.user_id = :user_id AND denied.code = effective_permissions.code
            )
            ORDER BY code
            """
        ),
        {"user_id": user_id},
    )
    return [str(code) for code in result.scalars().all()]


async def list_all_permission_codes(session: AsyncSession) -> list[str]:
    result = await session.execute(text("SELECT code FROM permissions ORDER BY code"))
    return [str(code) for code in result.scalars().all()]


async def get_active_user(session: AsyncSession, user_id: UUID) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id, User.status == "ACTIVE"))
    return result.scalar_one_or_none()


async def get_active_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email, User.status == "ACTIVE"))
    return result.scalar_one_or_none()


async def user_exists_by_email(session: AsyncSession, email: str) -> bool:
    result = await session.execute(select(User.id).where(User.email == email, User.status != "DELETED"))
    return result.scalar_one_or_none() is not None


async def delete_registration_token_by_email(session: AsyncSession, email: str) -> None:
    await session.execute(text("DELETE FROM registration_verification_tokens WHERE email = :email"), {"email": email})


async def insert_registration_token(
    session: AsyncSession,
    *,
    token: str,
    code: str,
    email: str,
    password_hash: str,
    display_name: str,
    expires_at: datetime,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO registration_verification_tokens
                (token, code, email, password_hash, display_name, expires_at)
            VALUES
                (:token, :code, :email, :password_hash, :display_name, :expires_at)
            """
        ),
        {
            "token": token,
            "code": code,
            "email": email,
            "password_hash": password_hash,
            "display_name": display_name,
            "expires_at": expires_at,
        },
    )


async def get_registration_token_by_email_for_update(session: AsyncSession, email: str) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT email, password_hash, display_name
            FROM registration_verification_tokens
            WHERE email = :email
            FOR UPDATE
            """
        ),
        {"email": email},
    )
    row = result.mappings().one_or_none()
    return dict(row) if row else None


async def get_registration_token_for_verify(
    session: AsyncSession,
    *,
    token: str | None,
    email: str | None,
    code: str | None,
) -> dict | None:
    if token:
        result = await session.execute(
            text("SELECT * FROM registration_verification_tokens WHERE token = :token FOR UPDATE"),
            {"token": token},
        )
    else:
        result = await session.execute(
            text(
                """
                SELECT * FROM registration_verification_tokens
                WHERE email = :email AND code = :code
                FOR UPDATE
                """
            ),
            {"email": email, "code": code},
        )
    row = result.mappings().one_or_none()
    return dict(row) if row else None


async def add_user(session: AsyncSession, user: User) -> None:
    session.add(user)


async def delete_password_reset_by_email(session: AsyncSession, email: str) -> None:
    await session.execute(text("DELETE FROM password_reset_tokens WHERE email = :email"), {"email": email})


async def insert_password_reset_token(
    session: AsyncSession,
    *,
    token: str,
    email: str,
    code: str,
    verification_token: str,
    expires_at: datetime,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO password_reset_tokens (token, email, code, verification_token, expires_at)
            VALUES (:token, :email, :code, :verification_token, :expires_at)
            """
        ),
        {
            "token": token,
            "email": email,
            "code": code,
            "verification_token": verification_token,
            "expires_at": expires_at,
        },
    )


async def get_password_reset_by_email_for_update(session: AsyncSession, email: str) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT email FROM password_reset_tokens
            WHERE email = :email
            FOR UPDATE
            """
        ),
        {"email": email},
    )
    row = result.mappings().one_or_none()
    return dict(row) if row else None


async def get_password_reset_for_verify(
    session: AsyncSession,
    *,
    token: str | None,
    email: str | None,
    code: str | None,
) -> dict | None:
    if token:
        result = await session.execute(
            text(
                """
                SELECT token, expires_at FROM password_reset_tokens
                WHERE verification_token = :token
                FOR UPDATE
                """
            ),
            {"token": token},
        )
    else:
        result = await session.execute(
            text(
                """
                SELECT token, expires_at FROM password_reset_tokens
                WHERE email = :email AND code = :code
                FOR UPDATE
                """
            ),
            {"email": email, "code": code},
        )
    row = result.mappings().one_or_none()
    return dict(row) if row else None


async def get_password_reset_by_token_for_update(session: AsyncSession, token: str) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT email, expires_at FROM password_reset_tokens
            WHERE token = :token
            FOR UPDATE
            """
        ),
        {"token": token},
    )
    row = result.mappings().one_or_none()
    return dict(row) if row else None


async def delete_password_reset_by_token(session: AsyncSession, token: str) -> None:
    await session.execute(text("DELETE FROM password_reset_tokens WHERE token = :token"), {"token": token})
