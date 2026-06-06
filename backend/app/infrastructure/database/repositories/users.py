from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.users.entities import LoyaltyTransactionType, UserStatus
from app.domain.users.repositories import LoyaltyRepository, UserRepository
from app.infrastructure.database.models import LoyaltyTransaction, User


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_deletable_user_for_update(self, user_id: UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .where(User.status != UserStatus.DELETED)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_user_for_update(self, user_id: UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .where(User.status == UserStatus.ACTIVE)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, user: User) -> None:
        self._session.add(user)


class SqlAlchemyLoyaltyRepository(LoyaltyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_revoke_transaction(
        self,
        *,
        user_id: UUID,
        points: int,
        balance_before: int,
        reason: str,
    ) -> None:
        transaction = LoyaltyTransaction(
            id=uuid4(),
            user_id=user_id,
            order_id=None,
            type=LoyaltyTransactionType.REVOKE,
            points=points,
            balance_before=balance_before,
            balance_after=0,
            reason=reason,
            metadata_json={"source": "ACCOUNT_DELETION"},
        )
        self._session.add(transaction)

    async def add_redeem_transaction(
        self,
        *,
        user_id: UUID,
        order_id: UUID,
        points: int,
        balance_before: int,
        balance_after: int,
        reason: str,
    ) -> None:
        transaction = LoyaltyTransaction(
            id=uuid4(),
            user_id=user_id,
            order_id=order_id,
            type=LoyaltyTransactionType.REDEEM,
            points=points,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason,
            metadata_json={"source": "CHECKOUT"},
        )
        self._session.add(transaction)


async def prepare_account_deletion_security_tables(session: AsyncSession) -> None:
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('emv_auth_security_tables'))"))
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
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                rotated_at TIMESTAMPTZ
            )
            """
        )
    )


async def revoke_user_refresh_sessions(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        text("UPDATE refresh_token_sessions SET revoked_at = NOW() WHERE user_id = :user_id"),
        {"user_id": user_id},
    )


async def upsert_account_deletion_revocation(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO auth_session_revocations (user_id, revoked_after, reason)
            VALUES (:user_id, NOW(), 'account_deleted')
            ON CONFLICT (user_id)
            DO UPDATE SET revoked_after = EXCLUDED.revoked_after, reason = EXCLUDED.reason, created_at = NOW()
            """
        ),
        {"user_id": user_id},
    )


async def insert_account_deleted_security_audit(
    session: AsyncSession,
    *,
    user_id: UUID,
    ip_address: str,
    user_agent: str | None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO security_audit_logs
                (user_id, event_type, ip_address, user_agent, metadata)
            VALUES
                (:user_id, 'account_deleted', :ip_address, :user_agent, '{}'::jsonb)
            """
        ),
        {
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
        },
    )
