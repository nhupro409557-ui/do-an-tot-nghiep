from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories import order_repo


async def list_orders(session: AsyncSession, user_id: UUID | None = None) -> list[dict]:
    return await order_repo.list_orders(session, user_id)


async def get_order_detail(session: AsyncSession, order_id: UUID) -> dict:
    order = await order_repo.get_order_detail(session, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
    return order
