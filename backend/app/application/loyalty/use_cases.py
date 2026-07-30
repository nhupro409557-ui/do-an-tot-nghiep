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
                raise UserNotFoundError("Không tìm thấy tài khoản đang hoạt động.")

            from app.application.services.loyalty_maintenance_service import expire_user_points
            synced_balance = await expire_user_points(self._session, user_id=user.id)
            if synced_balance is not None:
                user.loyalty_points_balance = synced_balance

            if user.loyalty_wallet_status != LoyaltyWalletStatus.ACTIVE:
                raise LoyaltyWalletClosedError("Ví điểm thưởng không ở trạng thái hoạt động.")

            balance_before = int(user.loyalty_points_balance)
            if balance_before < points:
                raise InsufficientPointsError("Không đủ điểm thưởng.")

            balance_after = balance_before - points
            await loyalty_repo.add_redeem_transaction(
                user_id=user.id,
                order_id=order_id,
                points=points,
                balance_before=balance_before,
                balance_after=balance_after,
                reason="Đổi điểm thưởng khi thanh toán.",
            )
            user.loyalty_points_balance = balance_after
            await user_repo.save(user)

        return RedeemPointsResponse(
            user_id=user_id,
            order_id=order_id,
            redeemed_points=points,
            balance_after=balance_after,
        )
