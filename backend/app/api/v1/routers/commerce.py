from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.commerce.schemas import (
    AdminUpdateOrderRequest,
    ClaimVoucherRequest,
    CreateOrderRequest,
    CreateOrderResponse,
    RevenueReportResponse,
    ShippingQuoteRequest,
    ShippingQuoteResponse,
    UpdateOrderStatusRequest,
    UserVoucherResponse,
    VoucherValidationRequest,
    VoucherValidationResponse,
)
from app.application.commerce.use_cases import (
    CompleteOrderUseCase,
    CreateOrderUseCase,
    ReportUseCase,
    ShippingQuoteUseCase,
    VoucherService,
)
from app.infrastructure.database.session import get_session


router = APIRouter(tags=["Commerce"])


@router.post("/orders/shipping-quote", response_model=ShippingQuoteResponse)
async def quote_shipping(payload: ShippingQuoteRequest) -> ShippingQuoteResponse:
    return ShippingQuoteUseCase().execute(
        shipping_address=payload.shipping_address,
        subtotal_amount=payload.subtotal_amount,
        item_count=payload.item_count,
    )


@router.get("/orders")
async def list_orders(user_id: UUID | None = None, session: AsyncSession = Depends(get_session)) -> list[dict]:
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
            GROUP BY o.id
            ORDER BY o.created_at DESC
            """
        ),
        {"user_id": user_id},
    )
    return [dict(row._mapping) for row in result]


@router.get("/orders/{order_id}")
async def get_order_detail(order_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
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
                COALESCE(
                    jsonb_agg(
                        DISTINCT jsonb_build_object(
                            'id', oi.id::text,
                            'productId', oi.product_id::text,
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
                            'checkoutUrl', pt.checkout_url
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
            GROUP BY o.id
            """
        ),
        {"order_id": order_id},
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return dict(row._mapping)


@router.get("/vouchers")
async def list_vouchers(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        text(
            """
            SELECT
                id::text,
                code,
                discount_type AS "discountType",
                discount_value AS "discountAmount",
                min_order_value AS "minOrderValue",
                max_discount AS "maxDiscount",
                status,
                status = 'ACTIVE' AS "isActive"
            FROM vouchers
            ORDER BY created_at DESC
            """
        )
    )
    return [dict(row._mapping) for row in result]


@router.post("/vouchers/validate", response_model=VoucherValidationResponse)
async def validate_voucher(
    payload: VoucherValidationRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> VoucherValidationResponse:
    return await VoucherService(session=session).validate(
        code=payload.code,
        subtotal_amount=payload.subtotal_amount,
        user_id=payload.user_id,
        user_tier=payload.user_tier,
        abandoned_cart_recovery=payload.abandoned_cart_recovery,
        device_id=payload.device_id,
        ip_address=payload.ip_address or (request.client.host if request.client else None),
        product_ids=set(payload.product_ids),
        category_ids=set(payload.category_ids),
    )


@router.post("/vouchers/{voucher_id}/claim", response_model=UserVoucherResponse, status_code=status.HTTP_201_CREATED)
async def claim_voucher(
    voucher_id: UUID,
    payload: ClaimVoucherRequest,
    session: AsyncSession = Depends(get_session),
) -> UserVoucherResponse:
    response = await VoucherService(session=session).claim_voucher(user_id=payload.user_id, voucher_id=voucher_id)
    await session.commit()
    return response


@router.get("/users/{user_id}/vouchers", response_model=list[UserVoucherResponse])
async def list_user_vouchers(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[UserVoucherResponse]:
    responses = await VoucherService(session=session).list_user_vouchers(user_id=user_id)
    await session.commit()
    return responses


@router.post(
    "/orders",
    response_model=CreateOrderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid voucher or insufficient points."},
        404: {"description": "User not found."},
        409: {"description": "Loyalty wallet is closed."},
    },
)
async def create_order(
    payload: CreateOrderRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
) -> CreateOrderResponse:
    if payload.voucher_code and not payload.voucher_ip_address and request.client:
        payload.voucher_ip_address = request.client.host
    if idempotency_key and not payload.idempotency_key:
        payload.idempotency_key = idempotency_key
    return await CreateOrderUseCase(session=session).execute(payload)


@router.patch(
    "/orders/{order_id}/status",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Order not found."}},
)
async def update_order_status(
    order_id: UUID,
    payload: UpdateOrderStatusRequest,
    session: AsyncSession = Depends(get_session),
) -> None:
    await CompleteOrderUseCase(session=session).execute(order_id=order_id, status_value=payload.status)


@router.patch(
    "/orders/{order_id}/admin",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Order not found."}, 409: {"description": "Invalid order transition."}},
)
async def admin_update_order(
    order_id: UUID,
    payload: AdminUpdateOrderRequest,
    session: AsyncSession = Depends(get_session),
) -> None:
    await CompleteOrderUseCase(session=session).execute_admin_update(order_id=order_id, request=payload)


@router.post("/orders/maintenance/expire-pending")
async def expire_pending_orders(session: AsyncSession = Depends(get_session)) -> dict:
    expired = await CompleteOrderUseCase(session=session).expire_pending_orders()
    return {"expired": expired}


@router.post("/payments/momo/ipn")
async def momo_ipn(payload: dict, session: AsyncSession = Depends(get_session)) -> dict:
    order_code = str(payload.get("orderId") or "")
    result_code = int(payload.get("resultCode") or -1)
    if not order_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing orderId.")
    order_result = await session.execute(text("SELECT id::text FROM orders WHERE order_code = :order_code"), {"order_code": order_code})
    row = order_result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if result_code == 0:
        await CompleteOrderUseCase(session=session).execute(
            order_id=UUID(row[0]),
            status_value="PAID",
            internal_note="MoMo sandbox IPN marked payment successful.",
            changed_by="momo-ipn",
        )
    else:
        await CompleteOrderUseCase(session=session).execute(
            order_id=UUID(row[0]),
            status_value="PAYMENT_FAILED",
            internal_note=f"MoMo sandbox payment failed with resultCode={result_code}.",
            changed_by="momo-ipn",
        )
    return {"ok": True}


@router.get("/reports/revenue", response_model=RevenueReportResponse)
async def revenue_report(session: AsyncSession = Depends(get_session)) -> RevenueReportResponse:
    return await ReportUseCase(session=session).revenue()
