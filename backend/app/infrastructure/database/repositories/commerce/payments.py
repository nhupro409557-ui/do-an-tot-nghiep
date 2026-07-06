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


async def get_checkout_url(session: AsyncSession, order_id: UUID) -> str | None:
    result = await session.execute(
        select(PaymentTransaction.checkout_url).where(PaymentTransaction.order_id == order_id).limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_payment_transaction(session: AsyncSession, order_id: UUID) -> PaymentTransaction | None:
    return await session.scalar(
        select(PaymentTransaction)
        .where(PaymentTransaction.order_id == order_id)
        .order_by(PaymentTransaction.attempt_number.desc(), PaymentTransaction.created_at.desc())
        .limit(1)
    )


async def get_payment_transaction(session: AsyncSession, payment_id: UUID) -> PaymentTransaction | None:
    return await session.scalar(select(PaymentTransaction).where(PaymentTransaction.id == payment_id))


async def get_payment_transaction_for_update(
    session: AsyncSession,
    *,
    order_id: UUID,
    provider: str,
) -> PaymentTransaction | None:
    return await session.scalar(
        select(PaymentTransaction)
        .where(
            PaymentTransaction.order_id == order_id,
            PaymentTransaction.provider == provider,
        )
        .order_by(PaymentTransaction.attempt_number.desc(), PaymentTransaction.created_at.desc())
        .with_for_update()
        .limit(1)
    )


async def get_payment_transaction_by_reference_for_update(
    session: AsyncSession,
    *,
    provider: str,
    transaction_ref: str,
) -> PaymentTransaction | None:
    return await session.scalar(
        select(PaymentTransaction)
        .where(
            PaymentTransaction.provider == provider,
            PaymentTransaction.transaction_ref == transaction_ref,
        )
        .with_for_update()
        .limit(1)
    )


async def expire_pending_payment_transactions(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        text(
            """
            UPDATE payment_transactions pt
            SET status = 'EXPIRED',
                failed_at = NOW(),
                updated_at = NOW(),
                raw_response = COALESCE(pt.raw_response, '{}'::jsonb)
                    || jsonb_build_object('failure_message', 'Phiên thanh toán đã hết hạn.')
            FROM orders o
            WHERE pt.order_id = o.id
              AND pt.status = 'PENDING'
              AND pt.expires_at IS NOT NULL
              AND pt.expires_at <= NOW()
            RETURNING pt.order_id, o.status AS order_status
            """
        )
    )
    await session.commit()
    return [dict(row) for row in result.mappings().all()]


async def create_webhook_event(
    session: AsyncSession,
    *,
    event_id: UUID,
    provider: str,
    event_key: str,
    order_id: UUID | None,
    payment_transaction_id: UUID | None,
    signature_valid: bool,
    payload: dict,
) -> bool:
    result = await session.execute(
        text(
            """
            INSERT INTO payment_webhook_events (
                id, provider, event_key, order_id, payment_transaction_id,
                signature_valid, processing_status, payload
            )
            VALUES (
                :id, :provider, :event_key, :order_id, :payment_transaction_id,
                :signature_valid, 'RECEIVED', CAST(:payload AS JSONB)
            )
            ON CONFLICT (provider, event_key) DO UPDATE
            SET id = EXCLUDED.id,
                order_id = EXCLUDED.order_id,
                payment_transaction_id = EXCLUDED.payment_transaction_id,
                signature_valid = EXCLUDED.signature_valid,
                processing_status = 'RECEIVED',
                payload = EXCLUDED.payload,
                error_message = NULL,
                processed_at = NULL,
                created_at = NOW()
            WHERE payment_webhook_events.processing_status = 'FAILED'
            RETURNING id
            """
        ),
        {
            "id": event_id,
            "provider": provider,
            "event_key": event_key,
            "order_id": order_id,
            "payment_transaction_id": payment_transaction_id,
            "signature_valid": signature_valid,
            "payload": json.dumps(payload, ensure_ascii=False),
        },
    )
    return result.scalar_one_or_none() is not None


async def finish_webhook_event(
    session: AsyncSession,
    *,
    event_id: UUID,
    processing_status: str,
    error_message: str | None = None,
) -> None:
    await session.execute(
        text(
            """
            UPDATE payment_webhook_events
            SET processing_status = :processing_status,
                error_message = :error_message,
                processed_at = NOW()
            WHERE id = :event_id
            """
        ),
        {
            "event_id": event_id,
            "processing_status": processing_status,
            "error_message": error_message,
        },
    )
