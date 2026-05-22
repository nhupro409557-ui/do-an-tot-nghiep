from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.users.schemas import DeleteAccountResponse
from app.domain.users.entities import LoyaltyWalletStatus, UserStatus
from app.domain.users.repositories import LoyaltyRepository, UserRepository
from app.shared.exceptions import LoyaltyWalletClosedError, UserNotFoundError


class DeleteAccountUseCase:
    def __init__(
        self,
        *,
        session: AsyncSession,
        user_repository: UserRepository,
        loyalty_repository: LoyaltyRepository,
    ) -> None:
        self._session = session
        self._user_repository = user_repository
        self._loyalty_repository = loyalty_repository

    async def execute(self, user_id: UUID) -> DeleteAccountResponse:
        async with self._session.begin():
            user = await self._user_repository.get_deletable_user_for_update(user_id)
            if user is None:
                raise UserNotFoundError("User not found or already deleted.")

            if user.loyalty_wallet_status == LoyaltyWalletStatus.CLOSED:
                raise LoyaltyWalletClosedError("Loyalty wallet is already closed.")

            balance_before = int(user.loyalty_points_balance)
            revoked_points = balance_before

            if revoked_points > 0:
                await self._loyalty_repository.add_revoke_transaction(
                    user_id=user.id,
                    points=revoked_points,
                    balance_before=balance_before,
                    reason="Account deletion: revoke all remaining loyalty points.",
                )

            user.loyalty_points_balance = 0
            user.loyalty_wallet_status = LoyaltyWalletStatus.CLOSED
            user.status = UserStatus.DELETED
            user.deleted_at = datetime.now(timezone.utc)
            user.updated_at = datetime.now(timezone.utc)
            await self._user_repository.save(user)

        return DeleteAccountResponse(
            user_id=user.id,
            status=UserStatus.DELETED,
            loyalty_wallet_status=LoyaltyWalletStatus.CLOSED,
            revoked_points=revoked_points,
        )

