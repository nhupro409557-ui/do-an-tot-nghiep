from datetime import datetime
from decimal import Decimal
import json
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    AIContextLog,
    LoyaltyTransaction,
    Order,
    OrderHistoryLog,
    OrderItem,
    PaymentTransaction,
    Product,
    User,
    UserVoucher,
    Voucher,
)


async def get_database_now(session: AsyncSession) -> datetime:
    result = await session.execute(text("SELECT NOW()"))
    return result.scalar_one()


async def get_user_created_at(session: AsyncSession, user_id: UUID) -> datetime | None:
    result = await session.execute(select(User.created_at).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_voucher_by_id(session: AsyncSession, voucher_id: UUID) -> Voucher | None:
    return await session.scalar(select(Voucher).where(Voucher.id == voucher_id))


async def get_active_voucher(session: AsyncSession, code: str) -> Voucher | None:
    result = await session.execute(
        select(Voucher).where(Voucher.code == code.upper()).where(Voucher.status == "ACTIVE")
    )
    return result.scalar_one_or_none()


async def get_active_voucher_for_update(session: AsyncSession, code: str) -> Voucher | None:
    return await session.scalar(
        select(Voucher)
        .where(Voucher.code == code.upper())
        .where(Voucher.status == "ACTIVE")
        .with_for_update()
    )


async def get_voucher_by_order_code_for_update(session: AsyncSession, voucher_code: str) -> Voucher | None:
    return await session.scalar(select(Voucher).where(Voucher.code == voucher_code.upper()).with_for_update())


async def get_existing_user_voucher(session: AsyncSession, *, user_id: UUID, voucher_id: UUID) -> UserVoucher | None:
    return await session.scalar(
        select(UserVoucher)
        .where(UserVoucher.user_id == user_id)
        .where(UserVoucher.voucher_id == voucher_id)
        .where(UserVoucher.status.in_(["AVAILABLE", "RESERVED", "USED"]))
    )


async def has_user_voucher_assignment(session: AsyncSession, *, user_id: UUID, voucher_id: UUID) -> bool:
    result = await session.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM user_vouchers
                WHERE user_id = :user_id
                  AND voucher_id = :voucher_id
                  AND status IN ('AVAILABLE', 'RESERVED', 'USED')
            )
            """
        ),
        {"user_id": user_id, "voucher_id": voucher_id},
    )
    return bool(result.scalar())


async def add_user_voucher(session: AsyncSession, wallet_voucher: UserVoucher) -> None:
    session.add(wallet_voucher)
    await session.flush()


async def list_user_vouchers_with_voucher(session: AsyncSession, user_id: UUID) -> list[tuple[UserVoucher, Voucher]]:
    result = await session.execute(
        select(UserVoucher, Voucher)
        .join(Voucher, Voucher.id == UserVoucher.voucher_id)
        .where(UserVoucher.user_id == user_id)
        .order_by(UserVoucher.claimed_at.desc())
    )
    return list(result.all())


async def get_claimed_voucher(session: AsyncSession, *, user_id: UUID, voucher_id: UUID) -> UserVoucher | None:
    result = await session.execute(
        select(UserVoucher)
        .where(UserVoucher.user_id == user_id)
        .where(UserVoucher.voucher_id == voucher_id)
        .order_by(UserVoucher.claimed_at.desc())
    )
    return result.scalar_one_or_none()


async def get_claimed_voucher_for_update(session: AsyncSession, *, user_id: UUID, voucher_id: UUID) -> UserVoucher | None:
    return await session.scalar(
        select(UserVoucher)
        .where(UserVoucher.user_id == user_id)
        .where(UserVoucher.voucher_id == voucher_id)
        .where(UserVoucher.status.in_(["AVAILABLE", "RESERVED"]))
        .order_by(UserVoucher.claimed_at.desc())
        .with_for_update()
    )


async def get_user_voucher_for_update(session: AsyncSession, wallet_voucher_id: UUID) -> UserVoucher | None:
    return await session.scalar(select(UserVoucher).where(UserVoucher.id == wallet_voucher_id).with_for_update())


def save_model(session: AsyncSession, item) -> None:
    session.add(item)


async def count_user_orders(session: AsyncSession, user_id: UUID) -> int:
    result = await session.execute(text("SELECT COUNT(*) FROM orders WHERE user_id = :user_id"), {"user_id": user_id})
    return int(result.scalar() or 0)


async def count_user_voucher_usage(session: AsyncSession, *, user_id: UUID, code: str) -> int:
    result = await session.execute(
        text("SELECT COUNT(*) FROM orders WHERE user_id = :user_id AND voucher_code = :code"),
        {"user_id": user_id, "code": code.upper()},
    )
    return int(result.scalar() or 0)


async def count_voucher_usage_by_identity(session: AsyncSession, *, column: str, value: str, code: str) -> int:
    if column not in {"voucher_device_id", "voucher_ip_address"}:
        return 0
    result = await session.execute(
        text(f"SELECT COUNT(*) FROM orders WHERE voucher_code = :code AND {column} = :value"),
        {"code": code.upper(), "value": value},
    )
    return int(result.scalar() or 0)
