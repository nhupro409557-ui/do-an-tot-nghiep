from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.loyalty.schemas import RedeemPointsResponse
from app.domain.users.entities import LoyaltyTransactionType, LoyaltyWalletStatus, UserStatus
from app.infrastructure.database.models import LoyaltyTransaction, User
from app.shared.exceptions import (
    InsufficientPointsError,
    LoyaltyWalletClosedError,
    UserNotFoundError,
)


class RedeemPointsUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def execute(self, *, user_id: UUID, order_id: UUID, points: int) -> RedeemPointsResponse:
        async with self._session.begin():
            stmt = (
                select(User)
                .where(User.id == user_id)
                .where(User.status == UserStatus.ACTIVE)
                .with_for_update()
            )
            result = await self._session.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                raise UserNotFoundError("Active user not found.")

            if user.loyalty_wallet_status != LoyaltyWalletStatus.ACTIVE:
                raise LoyaltyWalletClosedError("Loyalty wallet is not active.")

            balance_before = int(user.loyalty_points_balance)
            if balance_before < points:
                raise InsufficientPointsError("Insufficient loyalty points.")

            balance_after = balance_before - points
            self._session.add(
                LoyaltyTransaction(
                    id=uuid4(),
                    user_id=user.id,
                    order_id=order_id,
                    type=LoyaltyTransactionType.REDEEM,
                    points=points,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    reason="Redeem loyalty points for checkout.",
                    metadata_json={"source": "CHECKOUT"},
                )
            )
            user.loyalty_points_balance = balance_after
            self._session.add(user)

        return RedeemPointsResponse(
            user_id=user_id,
            order_id=order_id,
            redeemed_points=points,
            balance_after=balance_after,
        )
