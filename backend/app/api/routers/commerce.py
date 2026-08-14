import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import order_service, payment_method_service, store_info_service
from app.infrastructure.database.models import Order
from app.infrastructure.database.repositories import auth_repo, commerce_repo, flash_sale_repo, order_repo, voucher_repo
from app.api.dependencies import get_current_user_id, get_optional_current_user_id, get_user_permissions, require_permission

from app.application.commerce.schemas import (
    AdminUpdateOrderRequest,
    CancelOrderRequest,
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


STAFF_ROLES = {"STAFF_ADMIN", "SUPER_ADMIN"}


def get_real_client_ip(request: Request) -> str:
    if "cf-connecting-ip" in request.headers:
        return request.headers["cf-connecting-ip"]
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _scoped_idempotency_key(raw_key: str, actor_scope: str) -> str:
    digest = hashlib.sha256(f"{actor_scope}:{raw_key}".encode("utf-8")).hexdigest()
    return f"scoped:{digest}"


async def _is_staff_or_admin(session: AsyncSession, user_id: UUID) -> bool:
    role = await auth_repo.get_active_user_role_code(session, user_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not active.")
    return role in STAFF_ROLES


async def _assert_order_access(
    session: AsyncSession,
    *,
    order_id: UUID,
    current_user_id: UUID,
) -> Order:
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
    role = await auth_repo.get_active_user_role_code(session, current_user_id)
    if role == "SUPER_ADMIN":
        return order
    if role == "STAFF_ADMIN":
        permissions = set(await auth_repo.list_permissions_for_user(session, current_user_id))
        if "order:read" in permissions:
            return order
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền xem đơn hàng.")
    if order.user_id and order.user_id == current_user_id:
        return order
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không có quyền truy cập đơn hàng này.")


async def _assert_payment_access(
    session: AsyncSession,
    *,
    payment_id: UUID,
    current_user_id: UUID,
) -> None:
    payment = await commerce_repo.get_payment_transaction(session, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch thanh toán.")
    await _assert_order_access(session, order_id=payment.order_id, current_user_id=current_user_id)


async def _resolve_requested_user_id(
    session: AsyncSession,
    *,
    requested_user_id: UUID | None,
    current_user_id: UUID | None,
) -> UUID | None:
    if requested_user_id is None:
        return current_user_id
    if current_user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Vui lòng đăng nhập để dùng thông tin tài khoản.")
    if requested_user_id == current_user_id:
        return current_user_id
    if await _is_staff_or_admin(session, current_user_id):
        return requested_user_id
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không được dùng thông tin tài khoản khác.")


async def _enforce_create_order_identity(
    session: AsyncSession,
    *,
    payload: CreateOrderRequest,
    current_user_id: UUID | None,
    request: Request,
) -> None:
    if payload.is_offline:
        if current_user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="POS cần đăng nhập nhân viên.")
        if not await _is_staff_or_admin(session, current_user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ nhân viên được tạo đơn POS.")
        actor_scope = f"staff:{current_user_id}"
    else:
        if current_user_id is None:
            if payload.user_id is not None or payload.loyalty_points_used > 0:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Vui lòng đăng nhập để dùng tài khoản hoặc điểm thưởng.")
            payload.user_id = None
            actor_scope = f"guest:{get_real_client_ip(request)}"
        else:
            if payload.user_id is not None and payload.user_id != current_user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không được tạo đơn cho tài khoản khác.")
            payload.user_id = current_user_id
            actor_scope = f"user:{current_user_id}"

    if payload.idempotency_key:
        payload.idempotency_key = _scoped_idempotency_key(payload.idempotency_key, actor_scope)


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
async def list_orders(
    user_id: UUID | None = None,
    _permission=Depends(require_permission("order:read")),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await order_service.list_orders(session, user_id)


@router.get("/orders/{order_id}")
async def get_order_detail(
    order_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    await _assert_order_access(session, order_id=order_id, current_user_id=current_user_id)
    return await order_service.get_order_detail(session, order_id)


@router.get("/payment-methods")
async def list_payment_methods(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await payment_method_service.list_public_payment_methods(session)


@router.get("/vouchers")
async def list_vouchers(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await voucher_repo.list_public_vouchers(session)


@router.get("/flash-sales/me/quotas")
async def list_my_flash_sale_quotas(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await flash_sale_repo.list_user_flash_sale_quotas(session, current_user_id)


@router.post("/vouchers/validate", response_model=VoucherValidationResponse)
async def validate_voucher(
    payload: VoucherValidationRequest,
    request: Request,
    current_user_id: UUID | None = Depends(get_optional_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> VoucherValidationResponse:
    effective_user_id = await _resolve_requested_user_id(
        session,
        requested_user_id=payload.user_id,
        current_user_id=current_user_id,
    )
    
    from app.api.routers.auth_utils import enforce_rate_limit, rate_limit_key
    rl_key = rate_limit_key(
        request,
        scope="voucher_validate",
        identity=str(effective_user_id) if effective_user_id else (payload.device_id or payload.ip_address)
    )
    try:
        enforce_rate_limit(rl_key, limit=10, window_seconds=60)
    except HTTPException as e:
        if e.status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Bạn đang kiểm tra voucher quá thường xuyên. Vui lòng thử lại sau.",
            )
        raise e

    if effective_user_id:
        user = await commerce_repo.get_user(session, effective_user_id)
        trusted_user_tier = user.loyalty_tier if user else None
    else:
        trusted_user_tier = None

    return await VoucherService(session=session).validate(
        code=payload.code,
        subtotal_amount=payload.subtotal_amount,
        user_id=effective_user_id,
        user_tier=trusted_user_tier,
        abandoned_cart_recovery=payload.abandoned_cart_recovery,
        device_id=payload.device_id,
        ip_address=payload.ip_address or get_real_client_ip(request),
        payment_method=payload.payment_method,
        channel=payload.channel,
        product_ids=set(payload.product_ids),
        category_ids=set(payload.category_ids),
        brand_ids=set(payload.brand_ids),
        items=payload.items,
    )


@router.post("/vouchers/{voucher_id}/claim", response_model=UserVoucherResponse, status_code=status.HTTP_201_CREATED)
async def claim_voucher(
    voucher_id: UUID,
    payload: ClaimVoucherRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> UserVoucherResponse:
    user_id = await _resolve_requested_user_id(
        session,
        requested_user_id=payload.user_id,
        current_user_id=current_user_id,
    )
    response = await VoucherService(session=session).claim_voucher(user_id=user_id, voucher_id=voucher_id)
    await session.commit()
    return response


@router.get("/users/{user_id}/vouchers", response_model=list[UserVoucherResponse])
async def list_user_vouchers(
    user_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[UserVoucherResponse]:
    user_id = await _resolve_requested_user_id(
        session,
        requested_user_id=user_id,
        current_user_id=current_user_id,
    )
    responses = await VoucherService(session=session).list_user_vouchers(user_id=user_id)
    return responses


@router.post(
    "/orders",
    response_model=CreateOrderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Voucher không hợp lệ hoặc không đủ điểm thưởng."},
        404: {"description": "Không tìm thấy tài khoản."},
        409: {"description": "Ví điểm thưởng đã đóng."},
    },
)
async def create_order(
    payload: CreateOrderRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user_id: UUID | None = Depends(get_optional_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> CreateOrderResponse:
    if payload.voucher_code and not payload.voucher_ip_address:
        payload.voucher_ip_address = get_real_client_ip(request)
    if idempotency_key and not payload.idempotency_key:
        payload.idempotency_key = idempotency_key
    await _enforce_create_order_identity(
        session,
        payload=payload,
        current_user_id=current_user_id,
        request=request,
    )
    return await CreateOrderUseCase(session=session).execute(payload)


@router.patch(
    "/orders/{order_id}/status",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Không tìm thấy đơn hàng."}},
)
async def update_order_status(
    order_id: UUID,
    payload: UpdateOrderStatusRequest,
    _permission=Depends(require_permission("order:update")),
    session: AsyncSession = Depends(get_session),
    permissions: set[str] = Depends(get_user_permissions),
    actor_id: UUID = Depends(get_current_user_id),
) -> None:
    if payload.status == "REFUNDED" and "order:refund" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền hoàn tiền đơn hàng.")
    if session.in_transaction():
        await session.rollback()
    await CompleteOrderUseCase(session=session).execute(
        order_id=order_id,
        status_value=payload.status,
        customer_receipt_confirmed=payload.customer_receipt_confirmed,
        actor_id=actor_id,
        changed_by=f"admin:{actor_id}",
    )


@router.post(
    "/orders/{order_id}/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"description": "Thiếu lý do hủy đơn."},
        403: {"description": "Không có quyền hủy đơn hàng này."},
        404: {"description": "Không tìm thấy đơn hàng."},
        409: {"description": "Đơn hàng không ở trạng thái hợp lệ để hủy."},
    },
)
async def cancel_my_order(
    order_id: UUID,
    payload: CancelOrderRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    order = await _assert_order_access(
        session,
        order_id=order_id,
        current_user_id=current_user_id,
    )
    if order.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ chủ đơn hàng được dùng chức năng hủy này. Nhân viên vui lòng xử lý trong màn quản trị đơn hàng.",
        )
    if order.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chỉ có thể tự hủy đơn khi đơn còn chờ xử lý. Đơn đã thanh toán cần liên hệ shop để hoàn tiền.",
        )

    if session.in_transaction():
        await session.rollback()

    await CompleteOrderUseCase(session=session).execute(
        order_id=order_id,
        status_value="CANCELLED",
        cancellation_reason=payload.reason,
        changed_by=f"user:{current_user_id}",
    )


@router.patch(
    "/orders/{order_id}/admin",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Không tìm thấy đơn hàng."}, 409: {"description": "Chuyển trạng thái đơn hàng không hợp lệ."}},
)
async def admin_update_order(
    order_id: UUID,
    payload: AdminUpdateOrderRequest,
    _permission=Depends(require_permission("order:update")),
    session: AsyncSession = Depends(get_session),
    permissions: set[str] = Depends(get_user_permissions),
    actor_id: UUID = Depends(get_current_user_id),
) -> None:
    if (payload.status == "REFUNDED" or payload.refund_payment) and "order:refund" not in permissions:
        raise HTTPException(status_code=403, detail="Bạn không có quyền hoàn tiền đơn hàng.")
    if session.in_transaction():
        await session.rollback()
    await CompleteOrderUseCase(session=session).execute_admin_update(
        order_id=order_id,
        request=payload,
        actor_id=actor_id,
    )


@router.post("/orders/{order_id}/carrier/quote", response_model=CarrierShipmentResponse)
async def quote_order_carrier(
    order_id: UUID,
    payload: CarrierQuoteRequest,
    _permission=Depends(require_permission("order:read")),
    session: AsyncSession = Depends(get_session),
) -> CarrierShipmentResponse:
    if session.in_transaction():
        await session.rollback()
    return await CompleteOrderUseCase(session=session).quote_carrier_shipment(order_id=order_id, provider=payload.provider)


@router.post("/orders/{order_id}/carrier/shipment", response_model=CarrierShipmentResponse)
async def create_order_carrier_shipment(
    order_id: UUID,
    payload: CarrierShipmentCreateRequest,
    _permission=Depends(require_permission("order:carrier")),
    session: AsyncSession = Depends(get_session),
) -> CarrierShipmentResponse:
    if session.in_transaction():
        await session.rollback()
    return await CompleteOrderUseCase(session=session).create_carrier_shipment(order_id=order_id, provider=payload.provider)


@router.post("/orders/{order_id}/carrier/cancel", response_model=CarrierShipmentResponse)
async def cancel_order_carrier_shipment(
    order_id: UUID,
    payload: CarrierShipmentCancelRequest,
    _permission=Depends(require_permission("order:carrier")),
    session: AsyncSession = Depends(get_session),
) -> CarrierShipmentResponse:
    if session.in_transaction():
        await session.rollback()
    return await CompleteOrderUseCase(session=session).cancel_carrier_shipment(order_id=order_id, reason=payload.reason)


@router.post("/orders/{order_id}/carrier/events", response_model=CarrierShipmentResponse)
async def update_order_carrier_event(
    order_id: UUID,
    payload: CarrierShipmentEventRequest,
    _permission=Depends(require_permission("order:carrier")),
    session: AsyncSession = Depends(get_session),
) -> CarrierShipmentResponse:
    if session.in_transaction():
        await session.rollback()
    return await CompleteOrderUseCase(session=session).update_carrier_event(
        order_id=order_id,
        event_code=payload.event_code,
        note=payload.note,
    )


@router.post("/orders/maintenance/expire-pending")
async def expire_pending_orders(
    _permission=Depends(require_permission("order:maintenance")),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if session.in_transaction():
        await session.rollback()
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
    logger.info("SEPAY IPN received with content-type=%s", request.headers.get("content-type"))

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
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> PaymentStatusResponse:
    await _assert_payment_access(session, payment_id=payment_id, current_user_id=current_user_id)
    return await PaymentUseCase(session=session).get_status(payment_id)


@router.post("/payments/{payment_id}/retry", response_model=PaymentStatusResponse)
async def retry_payment(
    payment_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> PaymentStatusResponse:
    await _assert_payment_access(session, payment_id=payment_id, current_user_id=current_user_id)
    if session.in_transaction():
        await session.rollback()
    return await PaymentUseCase(session=session).retry(payment_id)


@router.post("/payments/{payment_id}/cancel", response_model=PaymentStatusResponse)
async def cancel_payment(
    payment_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> PaymentStatusResponse:
    await _assert_payment_access(session, payment_id=payment_id, current_user_id=current_user_id)
    if session.in_transaction():
        await session.rollback()
    return await PaymentUseCase(session=session).cancel(payment_id)


@router.get("/reports/revenue", response_model=RevenueReportResponse)
async def revenue_report(
    _permission=Depends(require_permission("report:revenue_read")),
    session: AsyncSession = Depends(get_session),
) -> RevenueReportResponse:
    return await ReportUseCase(session=session).revenue()


@router.get("/store/info")
async def get_store_info(session: AsyncSession = Depends(get_session)) -> dict:
    return await store_info_service.get_store_info(session)


@router.get("/store/policies")
async def get_public_store_policies(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await store_info_service.list_public_store_policies(session)


@router.get("/orders/{order_id}/invoice")
async def export_order_invoice(
    order_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> Response:
    from app.application.services import order_service
    from app.application.services.document_export_service import render_order_invoice_pdf

    await _assert_order_access(session, order_id=order_id, current_user_id=current_user_id)
    order = await order_service.get_order_detail(session, order_id)
    items = order.get("items") or []
    pdf_content, filename = render_order_invoice_pdf(order, items)

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
