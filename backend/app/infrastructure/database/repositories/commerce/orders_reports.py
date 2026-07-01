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
                payment_method = 'COD'
                AND created_at < NOW() - make_interval(hours => :cod_timeout_hours)
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
