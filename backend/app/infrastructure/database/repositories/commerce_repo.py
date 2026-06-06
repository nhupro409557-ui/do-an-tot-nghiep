from datetime import datetime
from decimal import Decimal
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


async def get_order_by_idempotency_key(session: AsyncSession, idempotency_key: str) -> Order | None:
    return await session.scalar(select(Order).where(Order.idempotency_key == idempotency_key))


async def get_user_for_update(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.scalar(select(User).where(User.id == user_id).with_for_update())


async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.scalar(select(User).where(User.id == user_id))


async def list_product_categories(session: AsyncSession, product_ids: list[UUID]) -> list:
    result = await session.execute(
        select(Product.id, Product.category_id, Product.subcategory_id).where(Product.id.in_(product_ids))
    )
    return list(result)


async def get_variant_inventory_for_update(
    session: AsyncSession,
    *,
    variant_id: UUID,
    product_id: UUID | None,
) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, product_id, stock_quantity
                FROM product_variants
                WHERE id = :variant_id
                  AND (:product_id IS NULL OR product_id = :product_id)
                  AND is_active = TRUE
                FOR UPDATE
                """
            ),
            {"variant_id": variant_id, "product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_product_inventory_for_update(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, stock_quantity
                FROM products
                WHERE id = :product_id AND status = 'ACTIVE'
                FOR UPDATE
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def update_variant_stock(session: AsyncSession, *, variant_id: UUID, quantity: int) -> None:
    await session.execute(
        text("UPDATE product_variants SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
        {"id": variant_id, "quantity": quantity},
    )


async def update_product_stock(session: AsyncSession, *, product_id: UUID, quantity: int) -> None:
    await session.execute(
        text("UPDATE products SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
        {"id": product_id, "quantity": quantity},
    )


async def insert_inventory_adjustment(
    session: AsyncSession,
    *,
    product_id: UUID,
    variant_id: UUID | None,
    old_quantity: int,
    new_quantity: int,
    delta: int,
    transaction_type: str,
    reference_code: str,
    reason: str,
    note: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO inventory_adjustment_logs (
                id, product_id, variant_id, old_quantity, new_quantity, delta,
                transaction_type, reference_code, reason, note
            )
            VALUES (
                :id, :product_id, :variant_id, :old_quantity, :new_quantity, :delta,
                :transaction_type, :reference_code, :reason, :note
            )
            """
        ),
        {
            "id": uuid4(),
            "product_id": product_id,
            "variant_id": variant_id,
            "old_quantity": old_quantity,
            "new_quantity": new_quantity,
            "delta": delta,
            "transaction_type": transaction_type,
            "reference_code": reference_code,
            "reason": reason,
            "note": note,
        },
    )


async def get_checkout_url(session: AsyncSession, order_id: UUID) -> str | None:
    result = await session.execute(
        select(PaymentTransaction.checkout_url).where(PaymentTransaction.order_id == order_id).limit(1)
    )
    return result.scalar_one_or_none()


async def get_order_for_update(session: AsyncSession, order_id: UUID) -> Order | None:
    return await session.scalar(select(Order).where(Order.id == order_id).with_for_update())


async def list_pending_order_ids_to_expire(
    session: AsyncSession,
    *,
    online_timeout_minutes: int,
    cod_timeout_hours: int,
) -> list[UUID]:
    result = await session.execute(
        text(
            """
            SELECT id
            FROM orders
            WHERE status = 'PENDING'
              AND (
                (payment_method <> 'COD' AND created_at < NOW() - make_interval(mins => :online_timeout_minutes))
                OR
                (payment_method = 'COD' AND created_at < NOW() - make_interval(hours => :cod_timeout_hours))
              )
            ORDER BY created_at ASC
            """
        ),
        {"online_timeout_minutes": online_timeout_minutes, "cod_timeout_hours": cod_timeout_hours},
    )
    return [row[0] for row in result.all()]


async def list_payment_transactions_for_update(session: AsyncSession, order_id: UUID) -> list[PaymentTransaction]:
    payment_rows = await session.execute(
        select(PaymentTransaction).where(PaymentTransaction.order_id == order_id).with_for_update()
    )
    return list(payment_rows.scalars().all())


async def list_restock_items(session: AsyncSession, *, order_id: UUID, order_code: str) -> list[dict]:
    item_rows = await session.execute(
        text(
            """
            SELECT
                oi.id,
                oi.product_id,
                oi.variant_id AS order_variant_id,
                oi.product_name,
                oi.quantity,
                logs.variant_id
            FROM order_items oi
            LEFT JOIN LATERAL (
                SELECT ial.variant_id
                FROM inventory_adjustment_logs ial
                WHERE ial.reference_code = :reference_code
                  AND ial.product_id IS NOT DISTINCT FROM oi.product_id
                  AND ial.reason = 'ORDER_CREATED'
                ORDER BY ial.created_at ASC
                LIMIT 1
            ) logs ON TRUE
            WHERE oi.order_id = :order_id
            """
        ),
        {"order_id": order_id, "reference_code": order_code},
    )
    return [dict(item) for item in item_rows.mappings().all()]


async def get_variant_stock_for_update(session: AsyncSession, variant_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, product_id, stock_quantity
                FROM product_variants
                WHERE id = :variant_id
                FOR UPDATE
                """
            ),
            {"variant_id": variant_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_product_stock_for_update(session: AsyncSession, product_id: UUID) -> dict | None:
    row = (
        await session.execute(
            text(
                """
                SELECT id, stock_quantity
                FROM products
                WHERE id = :product_id
                FOR UPDATE
                """
            ),
            {"product_id": product_id},
        )
    ).mappings().first()
    return dict(row) if row else None


async def get_revenue_report(session: AsyncSession) -> dict:
    total_orders = await session.scalar(select(func.count(Order.id)))
    completed_orders = await session.scalar(select(func.count(Order.id)).where(Order.status == "COMPLETED"))
    total_revenue = await session.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.status == "COMPLETED")
    )
    ai_interactions = await session.scalar(select(func.count(AIContextLog.id)))
    loyalty_points_used = await session.scalar(select(func.coalesce(func.sum(Order.loyalty_points_used), 0)))
    return {
        "total_orders": total_orders or 0,
        "completed_orders": completed_orders or 0,
        "total_revenue": total_revenue or Decimal("0"),
        "ai_interactions": ai_interactions or 0,
        "loyalty_points_used": loyalty_points_used or 0,
    }
