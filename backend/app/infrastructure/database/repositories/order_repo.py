from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories.warranty_snapshot import (
    order_item_effective_warranty_months_sql,
    order_item_extra_warranty_months_lateral_sql,
)


def order_item_identifiers_sql() -> str:
    return """
        COALESCE((
            SELECT jsonb_agg(raw.identifier ORDER BY raw.sort_key)
            FROM (
                SELECT
                    0 AS sort_key,
                    jsonb_build_object(
                        'imei', ud.imei,
                        'secondaryImei', NULL,
                        'serialNumber', ud.serial_number,
                        'deviceStatus', ud.status
                    ) AS identifier
                WHERE oi.used_device_id IS NOT NULL

                UNION ALL

                SELECT
                    1 AS sort_key,
                    jsonb_build_object(
                        'imei', pi.imei,
                        'secondaryImei',
                            CASE
                                WHEN pair.imei1 = pi.imei THEN pair.imei2
                                WHEN pair.imei2 = pi.imei THEN pair.imei1
                                ELSE NULL
                            END,
                        'serialNumber', pair.serial_number,
                        'deviceStatus', pi.status
                    ) AS identifier
                FROM product_imeis pi
                LEFT JOIN product_identifier_pairs pair
                  ON pair.product_id = pi.product_id
                 AND pair.variant_id IS NOT DISTINCT FROM pi.variant_id
                 AND (pair.imei1 = pi.imei OR pair.imei2 = pi.imei)
                WHERE oi.used_device_id IS NULL
                  AND pi.sold_order_id = o.id
                  AND pi.product_id = COALESCE(oi.product_id, ud.product_id)
                  AND pi.variant_id IS NOT DISTINCT FROM COALESCE(oi.variant_id, ud.variant_id)
                  AND (pair.id IS NULL OR pi.imei = pair.imei1)

                UNION ALL

                SELECT
                    2 AS sort_key,
                    jsonb_build_object(
                        'imei', NULL,
                        'secondaryImei', NULL,
                        'serialNumber', psn.serial_number,
                        'deviceStatus', psn.status
                    ) AS identifier
                FROM product_serial_numbers psn
                WHERE oi.used_device_id IS NULL
                  AND psn.product_id = COALESCE(oi.product_id, ud.product_id)
                  AND psn.variant_id IS NOT DISTINCT FROM COALESCE(oi.variant_id, ud.variant_id)
                  AND (
                      psn.service_payload ->> 'soldOrderId' = o.id::text
                      OR psn.service_payload ->> 'orderId' = o.id::text
                  )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM product_identifier_pairs pair
                      WHERE pair.product_id = psn.product_id
                        AND pair.variant_id IS NOT DISTINCT FROM psn.variant_id
                        AND pair.serial_number = psn.serial_number
                  )
            ) raw
            WHERE raw.identifier ->> 'imei' IS NOT NULL
               OR raw.identifier ->> 'serialNumber' IS NOT NULL
        ), '[]'::jsonb)
    """


async def list_orders(session: AsyncSession, user_id: UUID | None = None) -> list[dict]:
    where = "WHERE o.user_id = :user_id" if user_id else ""
    warranty_months_sql = order_item_effective_warranty_months_sql()
    extra_warranty_join_sql = order_item_extra_warranty_months_lateral_sql()
    identifiers_sql = order_item_identifiers_sql()
    result = await session.execute(
        text(
            f"""
            SELECT
                o.id::text AS id,
                o.order_code AS "orderCode",
                o.order_purpose AS "orderType",
                o.source_order_id::text AS "sourceOrderId",
                o.payment_requirement AS "paymentRequirement",
                o.fulfillment_method AS "fulfillmentMethod",
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
                o.return_source AS "returnSource",
                o.return_reason AS "returnReason",
                o.return_tracking_code AS "returnTrackingCode",
                o.return_received_condition AS "returnReceivedCondition",
                o.return_received_at AS "returnReceivedAt",
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
                            'warrantyMonthsSnapshot', {warranty_months_sql},
                            'warrantySnapshotMissing', oi.warranty_months_snapshot IS NULL,
                            'attachedServices', COALESCE(oi.attached_services, '[]'::jsonb),
                            'identifiers', {identifiers_sql},
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
            LEFT JOIN products p ON p.id = oi.product_id
            LEFT JOIN used_devices ud ON ud.id = oi.used_device_id
            {extra_warranty_join_sql}
            {where}
            GROUP BY o.id, u.email, u.full_name
            ORDER BY o.created_at DESC
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row._mapping) for row in result]


async def get_order_detail(session: AsyncSession, order_id: UUID) -> dict | None:
    warranty_months_sql = order_item_effective_warranty_months_sql()
    extra_warranty_join_sql = order_item_extra_warranty_months_lateral_sql()
    identifiers_sql = order_item_identifiers_sql()
    result = await session.execute(
        text(
            f"""
            SELECT
                o.id::text AS id,
                o.order_code AS "orderCode",
                o.order_purpose AS "orderType",
                o.source_order_id::text AS "sourceOrderId",
                o.payment_requirement AS "paymentRequirement",
                o.fulfillment_method AS "fulfillmentMethod",
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
                o.return_source AS "returnSource",
                o.return_reason AS "returnReason",
                o.return_tracking_code AS "returnTrackingCode",
                o.return_received_condition AS "returnReceivedCondition",
                o.return_received_at AS "returnReceivedAt",
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
                            'warrantyMonthsSnapshot', {warranty_months_sql},
                            'warrantySnapshotMissing', oi.warranty_months_snapshot IS NULL,
                            'attachedServices', COALESCE(oi.attached_services, '[]'::jsonb),
                            'identifiers', {identifiers_sql},
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
                                'changedByName', COALESCE(changer.full_name, changer.email),
                                'changedByEmail', changer.email,
                                'changedByRole', changer_role.code,
                                'note', hl.note,
                                'createdAt', hl.created_at
                            )
                            ORDER BY hl.created_at DESC
                        )
                        FROM order_history_logs hl
                        LEFT JOIN users changer ON changer.id::text = hl.changed_by
                        LEFT JOIN roles changer_role ON changer_role.id = changer.role_id
                        WHERE hl.order_id = o.id
                    ),
                    '[]'::jsonb
                ) AS "historyLogs"
            FROM orders o
            LEFT JOIN users u ON u.id = o.user_id
            LEFT JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN products p ON p.id = oi.product_id
            LEFT JOIN used_devices ud ON ud.id = oi.used_device_id
            {extra_warranty_join_sql}
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
