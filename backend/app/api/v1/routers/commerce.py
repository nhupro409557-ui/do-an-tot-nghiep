from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import order_service
from app.infrastructure.database.repositories import order_repo, voucher_repo

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
    return await order_service.list_orders(session, user_id)


@router.get("/orders/{order_id}")
async def get_order_detail(order_id: UUID, session: AsyncSession = Depends(get_session)) -> dict:
    return await order_service.get_order_detail(session, order_id)


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
    order_id = await order_repo.get_order_id_by_code(session, order_code)
    if order_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    if result_code == 0:
        await CompleteOrderUseCase(session=session).execute(
            order_id=order_id,
            status_value="PAID",
            internal_note="MoMo sandbox IPN marked payment successful.",
            changed_by="momo-ipn",
        )
    else:
        await CompleteOrderUseCase(session=session).execute(
            order_id=order_id,
            status_value="PAYMENT_FAILED",
            internal_note=f"MoMo sandbox payment failed with resultCode={result_code}.",
            changed_by="momo-ipn",
        )
    return {"ok": True}


@router.get("/reports/revenue", response_model=RevenueReportResponse)
async def revenue_report(session: AsyncSession = Depends(get_session)) -> RevenueReportResponse:
    return await ReportUseCase(session=session).revenue()
