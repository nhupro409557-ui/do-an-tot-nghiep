from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.loyalty.schemas import RedeemPointsResponse
from app.domain.users.entities import LoyaltyWalletStatus
from app.infrastructure.database.repositories.users import (
    SqlAlchemyLoyaltyRepository,
    SqlAlchemyUserRepository,
)
from app.shared.exceptions import (
    InsufficientPointsError,
    LoyaltyWalletClosedError,
    UserNotFoundError,
)


class RedeemPointsUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, *, user_id: UUID, order_id: UUID, points: int) -> RedeemPointsResponse:
        user_repo = SqlAlchemyUserRepository(self._session)
        loyalty_repo = SqlAlchemyLoyaltyRepository(self._session)

        async with self._session.begin():
            user = await user_repo.get_active_user_for_update(user_id)

            if user is None:
                raise UserNotFoundError("Active user not found.")

            if user.loyalty_wallet_status != LoyaltyWalletStatus.ACTIVE:
                raise LoyaltyWalletClosedError("Loyalty wallet is not active.")

            balance_before = int(user.loyalty_points_balance)
            if balance_before < points:
                raise InsufficientPointsError("Insufficient loyalty points.")

            balance_after = balance_before - points
            await loyalty_repo.add_redeem_transaction(
                user_id=user.id,
                order_id=order_id,
                points=points,
                balance_before=balance_before,
                balance_after=balance_after,
                reason="Redeem loyalty points for checkout.",
            )
            user.loyalty_points_balance = balance_after
            await user_repo.save(user)

        return RedeemPointsResponse(
            user_id=user_id,
            order_id=order_id,
            redeemed_points=points,
            balance_after=balance_after,
        )
