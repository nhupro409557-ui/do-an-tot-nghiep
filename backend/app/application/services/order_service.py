from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import order_repo
from app.infrastructure.database.repositories import commerce_repo
from app.application.commerce.use_cases import CompleteOrderUseCase


async def list_orders(session: AsyncSession, user_id: UUID | None = None) -> list[dict]:
    return await order_repo.list_orders(session, user_id)


async def get_order_detail(session: AsyncSession, order_id: UUID) -> dict:
    order = await order_repo.get_order_detail(session, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
    return order


async def expire_pending_payments(session: AsyncSession) -> int:
    expired_rows = await commerce_repo.expire_pending_payment_transactions(session)
    pending_order_ids: list[UUID] = []
    seen: set[str] = set()
    for row in expired_rows:
        order_id = row.get("order_id")
        if row.get("order_status") != "PENDING" or order_id is None:
            continue
        key = str(order_id)
        if key in seen:
            continue
        pending_order_ids.append(order_id)
        seen.add(key)
    if session.in_transaction():
        await session.rollback()
    for order_id in pending_order_ids:
        await CompleteOrderUseCase(session=session).execute(
            order_id=order_id,
            status_value="PAYMENT_FAILED",
            internal_note="Phiên thanh toán online đã hết hạn.",
            changed_by="payment-maintenance",
        )
    return len(expired_rows)
