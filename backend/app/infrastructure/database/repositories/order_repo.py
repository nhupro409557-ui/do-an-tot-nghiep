from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_orders(session: AsyncSession, user_id: UUID | None = None) -> list[dict]:
    where = "WHERE o.user_id = :user_id" if user_id else ""
    result = await session.execute(
        text(
            f"""
            SELECT
                o.id::text AS id,
                o.order_code AS "orderCode",
                o.user_id::text AS "userId",
                u.email AS email,
                u.full_name AS "customerName",
                o.status,
                o.payment_method AS "paymentMethod",
                o.payment_status AS "paymentStatus",
                o.total_amount AS "totalAmount",
                o.loyalty_points_earned AS "pointsEarned",
                o.loyalty_points_used AS "pointsUsed",
                o.recipient_name AS "recipientName",
                o.recipient_phone AS "recipientPhone",
                o.shipping_address AS "shippingAddress",
                o.assigned_staff_name AS "assignedStaffName",
                o.internal_note AS "internalNote",
                o.cancellation_reason AS "cancellationReason",
                o.shipping_provider AS "shippingProvider",
                o.tracking_code AS "trackingCode",
                o.shipped_at AS "shippedAt",
                o.cancelled_at AS "cancelledAt",
                o.refunded_at AS "refundedAt",
                o.completed_at AS "completedAt",
                o.created_at AS "createdAt",
                COALESCE(
                    jsonb_agg(
                        jsonb_build_object(
                            'id', oi.id::text,
                            'productId', oi.product_id::text,
                            'usedDeviceId', oi.used_device_id::text,
                            'warrantyMonthsSnapshot', oi.warranty_months_snapshot,
                            'productName', oi.product_name,
                            'quantity', oi.quantity,
                            'price', oi.unit_price,
                            'totalPrice', oi.total_price
                        )
                    ) FILTER (WHERE oi.id IS NOT NULL),
                    '[]'::jsonb
                ) AS items
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            LEFT JOIN order_items oi ON oi.order_id = o.id
            {where}
            GROUP BY o.id, u.email, u.full_name
            ORDER BY o.created_at DESC
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row._mapping) for row in result]


async def get_order_detail(session: AsyncSession, order_id: UUID) -> dict | None:
    result = await session.execute(
        text(
            """
            SELECT
                o.id::text AS id,
                o.order_code AS "orderCode",
                o.user_id::text AS "userId",
                u.email AS email,
                u.full_name AS "customerName",
                o.status,
                o.payment_method AS "paymentMethod",
                o.payment_status AS "paymentStatus",
                o.subtotal_amount AS "subtotalAmount",
                o.discount_amount AS "discountAmount",
                o.shipping_fee AS "shippingFee",
                o.total_amount AS "totalAmount",
                o.loyalty_points_earned AS "pointsEarned",
                o.loyalty_points_used AS "pointsUsed",
                o.recipient_name AS "recipientName",
                o.recipient_phone AS "recipientPhone",
                o.shipping_address AS "shippingAddress",
                o.assigned_staff_name AS "assignedStaffName",
                o.internal_note AS "internalNote",
                o.cancellation_reason AS "cancellationReason",
                o.shipping_provider AS "shippingProvider",
                o.tracking_code AS "trackingCode",
                o.shipped_at AS "shippedAt",
                o.cancelled_at AS "cancelledAt",
                o.refunded_at AS "refundedAt",
                o.completed_at AS "completedAt",
                o.created_at AS "createdAt",
                (
                    SELECT jsonb_build_object(
                        'documentNo', d.document_no,
                        'status', d.status
                    )
                    FROM inventory_documents d
                    WHERE d.order_id = o.id AND d.document_type = 'OUTBOUND'
                    LIMIT 1
                ) AS "outboundDocument",
                COALESCE(
                    jsonb_agg(
                        DISTINCT jsonb_build_object(
                            'id', oi.id::text,
                            'productId', oi.product_id::text,
                            'usedDeviceId', oi.used_device_id::text,
                            'warrantyMonthsSnapshot', oi.warranty_months_snapshot,
                            'productName', oi.product_name,
                            'quantity', oi.quantity,
                            'price', oi.unit_price,
                            'totalPrice', oi.total_price
                        )
                    ) FILTER (WHERE oi.id IS NOT NULL),
                    '[]'::jsonb
                ) AS items,
                COALESCE(
                    jsonb_agg(
                        DISTINCT jsonb_build_object(
                            'id', pt.id::text,
                            'provider', pt.provider,
                            'amount', pt.amount,
                            'status', pt.status,
                            'transactionRef', pt.transaction_ref,
                            'checkoutUrl', pt.checkout_url,
                            'attemptNumber', pt.attempt_number,
                            'expiresAt', pt.expires_at,
                            'paidAt', pt.paid_at,
                            'failedAt', pt.failed_at,
                            'sandboxMode', pt.raw_response ->> 'mode',
                            'refundMode', pt.raw_response ->> 'refund_mode'
                        )
                    ) FILTER (WHERE pt.id IS NOT NULL),
                    '[]'::jsonb
                ) AS payments,
                COALESCE(
                    (
                        SELECT jsonb_agg(
                            jsonb_build_object(
                                'id', hl.id::text,
                                'oldStatus', hl.old_status,
                                'newStatus', hl.new_status,
                                'changedBy', hl.changed_by,
                                'note', hl.note,
                                'createdAt', hl.created_at
                            )
                            ORDER BY hl.created_at DESC
                        )
                        FROM order_history_logs hl
                        WHERE hl.order_id = o.id
                    ),
                    '[]'::jsonb
                ) AS historyLogs
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            LEFT JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN payment_transactions pt ON pt.order_id = o.id
            WHERE o.id = :order_id
            GROUP BY o.id, u.email, u.full_name
            """
        ),
        {"order_id": order_id},
    )
    row = result.first()
    return dict(row._mapping) if row else None


async def get_order_id_by_code(session: AsyncSession, order_code: str) -> UUID | None:
    result = await session.execute(
        text("SELECT id FROM orders WHERE order_code = :order_code"),
        {"order_code": order_code},
    )
    return result.scalar_one_or_none()
