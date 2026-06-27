from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models import PaymentMethod


async def list_payment_methods(session: AsyncSession) -> list[PaymentMethod]:
    stmt = select(PaymentMethod).order_by(PaymentMethod.created_at.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_payment_method_by_code(session: AsyncSession, code: str) -> PaymentMethod | None:
    stmt = select(PaymentMethod).where(PaymentMethod.code == code.upper())
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_payment_method_by_id(session: AsyncSession, method_id: UUID) -> PaymentMethod | None:
    stmt = select(PaymentMethod).where(PaymentMethod.id == method_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_payment_method(session: AsyncSession, method_id: UUID, params: dict) -> int:
    params_cleaned = {k: v for k, v in params.items() if k in {
        "name", "description", "is_active", "maintenance_message",
        "maintenance_starts_at", "maintenance_ends_at"
    }}
    params_cleaned["updated_at"] = datetime.now(timezone.utc)
    
    stmt = (
        update(PaymentMethod)
        .where(PaymentMethod.id == method_id)
        .values(**params_cleaned)
    )
    result = await session.execute(stmt)
    return int(result.rowcount or 0)
