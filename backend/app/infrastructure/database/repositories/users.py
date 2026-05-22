from uuid import UUID, uuid4

from sqlalchemy import select
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

