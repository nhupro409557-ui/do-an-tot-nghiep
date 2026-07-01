from .common import *
from .voucher_service import VoucherService
from .complete_order import CompleteOrderUseCase

class CreateOrderUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session
        self._shipping_pricing = SandboxShippingPricingService()
        self._momo_gateway = MoMoSandboxGateway()
        self._sepay_gateway = SePayPaymentGateway()
        self._zalopay_gateway = ZaloPaySandboxGateway()

    async def execute(self, request: CreateOrderRequest) -> CreateOrderResponse:
        if request.idempotency_key:
            existing = await commerce_repo.get_order_by_idempotency_key(self._session, request.idempotency_key)
            if existing is not None:
                latest_payment = await commerce_repo.get_latest_payment_transaction(self._session, existing.id)
                checkout_url = latest_payment.checkout_url if latest_payment else None
                response = CreateOrderResponse(
                    order_id=existing.id,
                    order_code=existing.order_code,
                    payment_method=existing.payment_method,
                    payment_status=existing.payment_status,
                    shipping_fee=Decimal(existing.shipping_fee or 0),
                    total_amount=Decimal(existing.total_amount or 0),
                    loyalty_points_earned=int(existing.loyalty_points_earned or 0),
                    checkout_url=checkout_url,
                    payment_transaction_id=latest_payment.id if latest_payment else None,
                    payment_expires_at=latest_payment.expires_at.isoformat() if latest_payment and latest_payment.expires_at else None,
                )
                await self._session.rollback()
                return response
            await self._session.rollback()

        # Validate payment method status
        from app.infrastructure.database.repositories import payment_method_repo
        from app.application.services.payment_method_service import check_availability

        pm = await payment_method_repo.get_payment_method_by_code(self._session, request.payment_method)
        if not pm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phương thức thanh toán '{request.payment_method}' không hợp lệ."
            )
        is_avail, error_msg = check_availability(pm)
        if not is_avail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg or "Phương thức thanh toán này hiện không khả dụng."
            )

        subtotal = sum(item.unit_price * item.quantity for item in request.items)
        shipping_quote = await self._shipping_pricing.quote(
            self._session,
            shipping_address=request.shipping.shipping_address,
            subtotal_amount=subtotal,
            item_count=sum(item.quantity for item in request.items),
            provider="MOCK_GHN",
            lat=request.shipping.lat,
            lng=request.shipping.lng,
        )


        voucher_discount = Decimal("0")
        wallet_claim_id: UUID | None = None
        await self._session.rollback()

        async with self._session.begin():
            user = None
            if request.user_id:
                user = await commerce_repo.get_user_for_update(self._session, request.user_id)
                if user is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
                if user.loyalty_wallet_status != "ACTIVE":
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Loyalty wallet is not active.")
                if request.loyalty_points_used > user.loyalty_points_balance:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient loyalty points.")

            product_ids = {str(item.product_id) for item in request.items if item.product_id}
            category_ids = {str(item.category_id) for item in request.items if item.category_id}
            brand_ids: set[str] = set()
            if product_ids:
                product_result = await commerce_repo.list_product_categories(
                    self._session,
                    [UUID(item) for item in product_ids],
                )
                if not category_ids:
                    category_ids = {
                        str(row.subcategory_id or row.category_id)
                        for row in product_result
                        if row.subcategory_id or row.category_id
                    }
                brand_ids = {str(row.brand_id) for row in product_result if row.brand_id}

            voucher = None
            voucher_service = VoucherService(session=self._session)
            if request.voucher_code:
                voucher = await commerce_repo.get_active_voucher_for_update(self._session, request.voucher_code)
                if voucher is None:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid voucher.")
                validation = await voucher_service.validate(
                    code=voucher.code,
                    subtotal_amount=subtotal,
                    user_id=request.user_id,
                    user_tier=user.loyalty_tier if user else None,
                    device_id=request.voucher_device_id,
                    ip_address=request.voucher_ip_address,
                    payment_method=request.payment_method,
                    channel="WEB",
                    product_ids=product_ids,
                    category_ids=category_ids,
                    brand_ids=brand_ids,
                )
                if not validation.valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": validation.error_code,
                            "message": validation.message,
                            "metadata": validation.metadata,
                        },
                    )
                voucher_discount = validation.discount_amount

            points_discount = Decimal(request.loyalty_points_used) * Decimal("1000")
            total = max(Decimal("0"), subtotal - voucher_discount - points_discount + shipping_quote.fee)
            earned_points = int(total // Decimal("10000"))
            order_id = uuid4()
            order_code = ""
            for _ in range(5):
                candidate = generate_order_code()
                if await order_repo.get_order_id_by_code(self._session, candidate) is None:
                    order_code = candidate
                    break
            if not order_code:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể tạo mã đơn hàng.")

            reservation_lines: dict[tuple[str, UUID], dict] = {}
            for item in request.items:
                if item.variant_id:
                    inventory_row = await commerce_repo.get_variant_inventory_for_update(
                        self._session,
                        variant_id=item.variant_id,
                        product_id=item.product_id,
                    )
                    if not inventory_row:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found.")
                    old_quantity = int(inventory_row["stock_quantity"] or 0)
                    reserved_quantity = await commerce_repo.get_active_reserved_quantity(
                        self._session,
                        product_id=None,
                        variant_id=item.variant_id,
                    )
                    reservation_key = ("variant", item.variant_id)
                    already_requested = int(reservation_lines.get(reservation_key, {}).get("quantity", 0))
                    if old_quantity - reserved_quantity - already_requested - item.quantity < 0:
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Not enough stock for {item.product_name}.")
                    reservation_lines[reservation_key] = {
                        "product_id": item.product_id or inventory_row["product_id"],
                        "variant_id": item.variant_id,
                        "quantity": already_requested + item.quantity,
                    }
                elif item.product_id:
                    inventory_row = await commerce_repo.get_product_inventory_for_update(self._session, item.product_id)
                    if not inventory_row:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
                    old_quantity = int(inventory_row["stock_quantity"] or 0)
                    reserved_quantity = await commerce_repo.get_active_reserved_quantity(
                        self._session,
                        product_id=item.product_id,
                        variant_id=None,
                    )
                    reservation_key = ("product", item.product_id)
                    already_requested = int(reservation_lines.get(reservation_key, {}).get("quantity", 0))
                    if old_quantity - reserved_quantity - already_requested - item.quantity < 0:
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Not enough stock for {item.product_name}.")
                    reservation_lines[reservation_key] = {
                        "product_id": item.product_id,
                        "variant_id": None,
                        "quantity": already_requested + item.quantity,
                    }

            if voucher is not None:
                claimed_voucher = await voucher_service.mark_voucher_used(
                    voucher=voucher,
                    order_id=order_id,
                    discount_amount=voucher_discount,
                    user_id=request.user_id,
                )
                wallet_claim_id = claimed_voucher.id if claimed_voucher else None
            order = Order(
                id=order_id,
                user_id=request.user_id,
                order_code=order_code,
                status="COMPLETED" if request.is_offline else "PENDING",
                payment_method=request.payment_method,
                payment_status="PAID" if request.is_offline else ("UNPAID" if request.payment_method == "COD" else "PENDING"),
                subtotal_amount=subtotal,
                discount_amount=voucher_discount + points_discount,
                shipping_fee=shipping_quote.fee,
                total_amount=total,
                loyalty_points_earned=earned_points,
                loyalty_points_used=request.loyalty_points_used,
                voucher_code=voucher.code if voucher else None,
                voucher_claim_id=wallet_claim_id,
                voucher_device_id=request.voucher_device_id,
                voucher_ip_address=request.voucher_ip_address,
                idempotency_key=request.idempotency_key,
                recipient_name=request.shipping.recipient_name,
                recipient_phone=request.shipping.recipient_phone,
                recipient_email=request.shipping.recipient_email,
                shipping_address=request.shipping.shipping_address,
                internal_note=f"[POS] {request.internal_note or ''}".strip() if request.is_offline else None,
                completed_at=datetime.now(timezone.utc) if request.is_offline else None,
            )
            commerce_repo.save_model(self._session, order)
            await self._session.flush()
            for line in reservation_lines.values():
                await commerce_repo.create_inventory_reservation(
                    self._session,
                    order_id=order.id,
                    order_code=order.order_code,
                    product_id=line["product_id"] if line["variant_id"] is None else None,
                    variant_id=line["variant_id"],
                    quantity=line["quantity"],
                )
            commerce_repo.save_model(
                self._session,
                OrderHistoryLog(
                    id=uuid4(),
                    order_id=order.id,
                    old_status=None,
                    new_status=order.status,
                    changed_by="admin-pos" if request.is_offline else "system-checkout",
                    note="Order created from POS." if request.is_offline else "Order created from checkout.",
                    metadata_json={"payment_method": order.payment_method},
                ),
            )

            pos_issue_allocations: list[dict] = []
            for item in request.items:
                order_item_id = uuid4()
                commerce_repo.save_model(
                    self._session,
                    OrderItem(
                        id=order_item_id,
                        order_id=order.id,
                        product_id=item.product_id,
                        variant_id=item.variant_id,
                        product_name=item.product_name,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        total_price=item.unit_price * item.quantity,
                    ),
                )
                if request.is_offline:
                    pos_issue_allocations.append(
                        {
                            "order_item_id": order_item_id,
                            "imeis": item.imeis,
                            "serial_numbers": item.serial_numbers,
                        }
                    )

            if request.is_offline:
                # Trừ kho thực tế bằng FIFO
                complete_use_case = CompleteOrderUseCase(session=self._session)
                await complete_use_case._ship_order_items(order, issue_allocations=pos_issue_allocations)

                # Đóng các reservations vừa tạo dưới dạng CONSUMED
                await commerce_repo.close_active_order_reservations(
                    self._session,
                    order_id=order.id,
                    status="CONSUMED",
                )

                # Cộng điểm tích lũy ngay lập tức cho đơn offline
                if user and earned_points > 0:
                    balance_before = user.loyalty_points_balance
                    user.loyalty_points_balance += earned_points
                    user.loyalty_tier = calculate_tier(user.loyalty_points_balance)
                    commerce_repo.save_model(
                        self._session,
                        LoyaltyTransaction(
                            id=uuid4(),
                            user_id=user.id,
                            order_id=order.id,
                            type=LoyaltyTransactionType.EARN,
                            points=earned_points,
                            balance_before=balance_before,
                            balance_after=user.loyalty_points_balance,
                            reason="Tích điểm khi mua hàng trực tiếp tại quầy.",
                            metadata_json={"order_code": order.order_code},
                        ),
                    )
                    commerce_repo.save_model(self._session, user)

            checkout_url = None
            payment_transaction_id = None
            payment_expires_at = None
            if not request.is_offline and request.payment_method != "COD":
                if request.payment_method not in {"MOMO", "ZALOPAY", "SEPAY"}:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Hiện hệ thống chỉ hỗ trợ COD, MoMo Sandbox và ZaloPay Sandbox.",
                    )
                payment_transaction_id = uuid4()
                timeout_minutes_by_provider = {
                    "MOMO": settings.momo_payment_timeout_minutes,
                    "ZALOPAY": settings.zalopay_payment_timeout_minutes,
                    "SEPAY": settings.sepay_payment_timeout_minutes,
                }
                timeout_minutes = timeout_minutes_by_provider[request.payment_method]
                payment_expires_at = datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
                if request.payment_method == "MOMO":
                    provider_order_id = f"{order.order_code}-1"
                    payment_init = await self._momo_gateway.create_payment(
                        order_code=provider_order_id,
                        amount=total,
                        order_info=f"Thanh toán đơn hàng {order.order_code}",
                        extra_data={"orderCode": order.order_code, "userId": str(request.user_id) if request.user_id else ""},
                        request_id=str(payment_transaction_id),
                    )
                elif request.payment_method == "ZALOPAY":
                    vietnam_date = datetime.now(timezone(timedelta(hours=7))).strftime("%y%m%d")
                    provider_order_id = f"{vietnam_date}_{order.order_code[-10:]}01"
                    payment_init = await self._zalopay_gateway.create_payment(
                        app_trans_id=provider_order_id,
                        amount=total,
                        app_user=str(request.user_id or "electromart-sandbox"),
                        description=f"ElectroMart Sandbox - Thanh toán đơn hàng {order.order_code}",
                        callback_url=settings.zalopay_callback_url,
                        redirect_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_transaction_id}",
                    )
                else:
                    provider_order_id = f"{order.order_code}-1"
                    payment_init = self._sepay_gateway.create_checkout(
                        order_invoice_number=provider_order_id,
                        order_amount=total,
                        order_description=f"Thanh toán đơn hàng {order.order_code}",
                        success_url=f"{settings.frontend_url.rstrip('/')}/orders/{order.id}?payment=success",
                        error_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_transaction_id}?payment=error",
                        cancel_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_transaction_id}?payment=cancel",
                        customer_id=str(request.user_id) if request.user_id else None,
                    )
                checkout_url = payment_init.checkout_url
                commerce_repo.save_model(
                    self._session,
                    PaymentTransaction(
                        id=payment_transaction_id,
                        order_id=order.id,
                        provider=request.payment_method,
                        amount=total,
                        status="PENDING",
                        transaction_ref=provider_order_id,
                        checkout_url=checkout_url,
                        attempt_number=1,
                        expires_at=payment_expires_at,
                        raw_response=(payment_init.raw_response if payment_init else {"mode": "sandbox"}),
                    ),
                )

            if user and request.loyalty_points_used > 0:
                balance_before = user.loyalty_points_balance
                user.loyalty_points_balance -= request.loyalty_points_used
                commerce_repo.save_model(
                    self._session,
                    LoyaltyTransaction(
                        id=uuid4(),
                        user_id=user.id,
                        order_id=order.id,
                        type=LoyaltyTransactionType.REDEEM,
                        points=request.loyalty_points_used,
                        balance_before=balance_before,
                        balance_after=user.loyalty_points_balance,
                        reason="Redeem loyalty points during checkout.",
                        metadata_json={"order_code": order.order_code},
                    ),
                )
                commerce_repo.save_model(self._session, user)

        return CreateOrderResponse(
            order_id=order.id,
            order_code=order.order_code,
            payment_method=order.payment_method,
            payment_status=order.payment_status,
            shipping_fee=shipping_quote.fee,
            total_amount=total,
            loyalty_points_earned=earned_points,
            checkout_url=checkout_url,
            payment_transaction_id=payment_transaction_id,
            payment_expires_at=payment_expires_at.isoformat() if payment_expires_at else None,
        )

    async def _existing_checkout_url(self, order_id: UUID) -> str | None:
        return await commerce_repo.get_checkout_url(self._session, order_id)
