from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import order_service, payment_method_service, store_info_service
from app.infrastructure.database.repositories import order_repo, voucher_repo
from app.api.dependencies import require_staff_or_admin

from app.application.commerce.schemas import (
    AdminUpdateOrderRequest,
    CarrierQuoteRequest,
    CarrierShipmentCancelRequest,
    CarrierShipmentCreateRequest,
    CarrierShipmentEventRequest,
    CarrierShipmentResponse,
    ClaimVoucherRequest,
    CreateOrderRequest,
    CreateOrderResponse,
    PaymentStatusResponse,
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
    PaymentUseCase,
    ReportUseCase,
    ShippingQuoteUseCase,
    VoucherService,
)
from app.infrastructure.database.session import get_session


router = APIRouter(tags=["Commerce"])


@router.post("/orders/shipping-quote", response_model=ShippingQuoteResponse)
async def quote_shipping(
    payload: ShippingQuoteRequest,
    session: AsyncSession = Depends(get_session),
) -> ShippingQuoteResponse:
    return await ShippingQuoteUseCase().execute(
        session,
        shipping_address=payload.shipping_address,
        subtotal_amount=payload.subtotal_amount,
        item_count=payload.item_count,
        provider=payload.provider,
        lat=payload.lat,
        lng=payload.lng,
    )
@router.get("/shipping-config")
async def get_shipping_config() -> dict:
    from app.config import settings
    return {
        "free_shipping_threshold": settings.sandbox_shipping_free_threshold
    }


@router.get("/orders")
async def list_orders(user_id: UUID | None = None, session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await order_service.list_orders(session, user_id)


@router.get("/orders/{order_id}")
async def get_order_detail(order_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await order_service.get_order_detail(session, order_id)


@router.get("/payment-methods")
async def list_payment_methods(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await payment_method_service.list_public_payment_methods(session)


@router.get("/vouchers")
async def list_vouchers(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await voucher_repo.list_public_vouchers(session)


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
        payment_method=payload.payment_method,
        channel=payload.channel,
        product_ids=set(payload.product_ids),
        category_ids=set(payload.category_ids),
        brand_ids=set(payload.brand_ids),
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
    _staff_user=Depends(require_staff_or_admin),
    session: AsyncSession = Depends(get_session),
) -> None:
    if session.in_transaction():
        await session.rollback()
    await CompleteOrderUseCase(session=session).execute_admin_update(order_id=order_id, request=payload)


@router.post("/orders/{order_id}/carrier/quote", response_model=CarrierShipmentResponse)
async def quote_order_carrier(
    order_id: UUID,
    payload: CarrierQuoteRequest,
    session: AsyncSession = Depends(get_session),
) -> CarrierShipmentResponse:
    return await CompleteOrderUseCase(session=session).quote_carrier_shipment(order_id=order_id, provider=payload.provider)


@router.post("/orders/{order_id}/carrier/shipment", response_model=CarrierShipmentResponse)
async def create_order_carrier_shipment(
    order_id: UUID,
    payload: CarrierShipmentCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> CarrierShipmentResponse:
    return await CompleteOrderUseCase(session=session).create_carrier_shipment(order_id=order_id, provider=payload.provider)


@router.post("/orders/{order_id}/carrier/cancel", response_model=CarrierShipmentResponse)
async def cancel_order_carrier_shipment(
    order_id: UUID,
    payload: CarrierShipmentCancelRequest,
    session: AsyncSession = Depends(get_session),
) -> CarrierShipmentResponse:
    return await CompleteOrderUseCase(session=session).cancel_carrier_shipment(order_id=order_id, reason=payload.reason)


@router.post("/orders/{order_id}/carrier/events", response_model=CarrierShipmentResponse)
async def update_order_carrier_event(
    order_id: UUID,
    payload: CarrierShipmentEventRequest,
    session: AsyncSession = Depends(get_session),
) -> CarrierShipmentResponse:
    return await CompleteOrderUseCase(session=session).update_carrier_event(
        order_id=order_id,
        event_code=payload.event_code,
        note=payload.note,
    )


@router.post("/orders/maintenance/expire-pending")
async def expire_pending_orders(session: AsyncSession = Depends(get_session)) -> dict:
    expired = await CompleteOrderUseCase(session=session).expire_pending_orders()
    expired_payments = await order_service.expire_pending_payments(session)
    return {"expiredOrders": expired, "expiredPayments": expired_payments}


@router.post("/payments/momo/ipn")
async def momo_ipn(payload: dict, session: AsyncSession = Depends(get_session)) -> dict:
    return await PaymentUseCase(session=session).process_momo_ipn(payload)


@router.post("/payments/sepay/ipn")
async def sepay_ipn(
    request: Request,
    x_secret_key: str | None = Header(default=None, alias="X-Secret-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    import logging
    logger = logging.getLogger("uvicorn.error")
    logger.info("SEPAY IPN headers: %s", dict(request.headers))
    logger.info("SEPAY IPN query credentials: X-Secret-Key=%s, Authorization=%s", x_secret_key, authorization)

    payload: dict = {}
    content_type = request.headers.get("content-type", "").lower()
    raw_body = (await request.body()).decode("utf-8", errors="replace").strip()
    if "application/json" in content_type:
        body = await request.json()
        payload = body if isinstance(body, dict) else {"raw": body}
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        payload = dict(form)
        if raw_body:
            payload.setdefault("body", raw_body)
    else:
        payload = {"body": raw_body} if raw_body else {}

    secret_key = x_secret_key
    if not secret_key and authorization:
        auth_lower = authorization.lower()
        if auth_lower.startswith("bearer ") or auth_lower.startswith("apikey "):
            secret_key = authorization[7:].strip()
        else:
            secret_key = authorization.strip()
    return await PaymentUseCase(session=session).process_sepay_ipn(payload, secret_key=secret_key)


@router.post("/payments/zalopay/callback")
async def zalopay_callback(payload: dict, session: AsyncSession = Depends(get_session)) -> dict:
    return await PaymentUseCase(session=session).process_zalopay_callback(payload)


@router.get("/payments/{payment_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> PaymentStatusResponse:
    return await PaymentUseCase(session=session).get_status(payment_id)


@router.post("/payments/{payment_id}/retry", response_model=PaymentStatusResponse)
async def retry_payment(
    payment_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> PaymentStatusResponse:
    return await PaymentUseCase(session=session).retry(payment_id)


@router.post("/payments/{payment_id}/cancel", response_model=PaymentStatusResponse)
async def cancel_payment(
    payment_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> PaymentStatusResponse:
    return await PaymentUseCase(session=session).cancel(payment_id)


@router.get("/reports/revenue", response_model=RevenueReportResponse)
async def revenue_report(session: AsyncSession = Depends(get_session)) -> RevenueReportResponse:
    return await ReportUseCase(session=session).revenue()


@router.get("/store/info")
async def get_store_info(session: AsyncSession = Depends(get_session)) -> dict:
    return await store_info_service.get_store_info(session)


@router.get("/orders/{order_id}/invoice")
async def export_order_invoice(
    order_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    from app.application.services import order_service
    from app.application.services.document_export_service import render_order_invoice_pdf

    order = await order_service.get_order_detail(session, order_id)
    items = order.get("items") or []
    pdf_content, filename = render_order_invoice_pdf(order, items)

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
