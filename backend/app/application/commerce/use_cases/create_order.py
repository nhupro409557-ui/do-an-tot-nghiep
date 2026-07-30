from .common import *
from dataclasses import field
from typing import Any
from app.application.commerce.schemas import CheckoutItem, VoucherItemPayload
from .voucher_service import VoucherService
from .complete_order import CompleteOrderUseCase
from app.infrastructure.database.repositories import flash_sale_repo, used_product_repo
from app.infrastructure.database.retry import connection_retry_on_deadlock


def _checkout_money(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _pos_shipping_fee(request: CreateOrderRequest, quoted_fee: object) -> Decimal:
    if request.is_offline:
        return Decimal("0.00")
    return _checkout_money(quoted_fee)


def _validate_pos_cash_received(request: CreateOrderRequest, total: Decimal) -> None:
    if not request.is_offline or request.payment_method != "COD" or total <= 0:
        return
    if request.cash_received is None or _checkout_money(request.cash_received) < total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số tiền khách đưa phải lớn hơn hoặc bằng tổng thanh toán tại quầy.",
        )


def _checkout_flash_sale_price(base_price: Decimal, discount_type: object, discount_value: object) -> Decimal:
    if base_price <= 0:
        return Decimal("0.00")
    discount_type_value = str(discount_type or "PERCENT").upper()
    discount_amount = Decimal(str(discount_value or 0))
    if discount_type_value == "PERCENT":
        return _checkout_money(base_price * (Decimal("1") - discount_amount / Decimal("100")))
    return _checkout_money(base_price - discount_amount)


async def _resolve_checkout_price(
    session: AsyncSession,
    row: dict,
    quantity: int,
    user_id: UUID | None,
    *,
    lock_quota: bool = False,
) -> tuple[Decimal, Decimal, UUID | None, int]:
    regular_price = _checkout_money(row.get("regular_unit_price") or row.get("unit_price") or 0)
    sale_id = row.get("flash_sale_id")
    if not sale_id:
        return regular_price, regular_price, None, 0

    remaining_quantity = row.get("flash_sale_remaining_quantity")
    eligible_quantity = quantity if remaining_quantity is None else min(quantity, int(remaining_quantity or 0))

    per_user_limit = row.get("flash_sale_per_user_limit")
    if per_user_limit is not None:
        if user_id is None:
            eligible_quantity = 0
        else:
            used_quantity = await flash_sale_repo.get_user_reserved_quantity(
                session, UUID(str(sale_id)), user_id, lock_quota=lock_quota
            )
            eligible_quantity = min(eligible_quantity, max(int(per_user_limit) - used_quantity, 0))

    sale_price = _checkout_flash_sale_price(
        regular_price,
        row.get("flash_sale_discount_type"),
        row.get("flash_sale_discount_value"),
    )
    if sale_price <= 0 or sale_price >= regular_price:
        return regular_price, regular_price, None, 0

    return sale_price, regular_price, UUID(str(sale_id)), eligible_quantity


def _variant_suffix(row: dict) -> str:
    parts = [
        row.get("configuration"),
        row.get("color_name"),
        row.get("storage"),
        row.get("ram"),
    ]
    unique_parts: list[str] = []
    seen: set[str] = set()
    for part in parts:
        text_value = str(part or "").strip()
        if not text_value or text_value.lower() in seen:
            continue
        unique_parts.append(text_value)
        seen.add(text_value.lower())
    return " / ".join(unique_parts)


@dataclass(frozen=True)
class ResolvedCheckoutLine:
    product_id: UUID | None
    variant_id: UUID | None
    used_device_id: UUID | None
    product_name: str
    quantity: int
    unit_price: Decimal
    stock_quantity: int
    category_id: UUID | None
    brand_id: UUID | None
    imeis: list[str]
    serial_numbers: list[str]
    warranty_months_snapshot: int | None = None
    flash_sale_id: UUID | None = None
    attached_services: list[dict] = field(default_factory=list)


async def _resolve_attached_services(session: AsyncSession, item: CheckoutItem) -> tuple[int, list[dict]]:
    extra_warranty_months = 0
    attached_services_list = []
    if item.attached_services:
        service_ids = [s.service_id for s in item.attached_services]
        res = await session.execute(
            text(
                """
                SELECT asv.id, asv.code, asv.name, asv.duration_months, asv.fixed_price, pas.override_price
                FROM attached_services asv
                JOIN product_attached_services pas ON pas.service_id = asv.id
                WHERE asv.id = ANY(:service_ids) AND asv.is_active = TRUE AND pas.product_id = :product_id
                """
            ),
            {"service_ids": service_ids, "product_id": item.product_id},
        )
        db_services = {
            row.id: {
                "code": row.code,
                "name": row.name,
                "duration_months": row.duration_months,
                "price": float(row.override_price if row.override_price is not None else row.fixed_price),
            }
            for row in res.all()
        }
        for s in item.attached_services:
            db_s = db_services.get(s.service_id)
            if not db_s:
                raise HTTPException(
                    status_code=400,
                    detail=f"Dịch vụ đính kèm {s.name} không tồn tại, đã ngưng hoạt động hoặc không áp dụng cho sản phẩm này."
                )
            expected_price = db_s["price"]
            client_price = float(s.price)
            if abs(expected_price - client_price) > 0.01:
                raise HTTPException(
                    status_code=400,
                    detail=f"Giá dịch vụ đính kèm {s.name} ({client_price:,.0f}đ) không khớp với giá hệ thống ({expected_price:,.0f}đ)."
                )
            if s.code != db_s["code"] or s.name != db_s["name"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Thông tin dịch vụ đính kèm {s.name} không khớp với hệ thống."
                )
            extra_warranty_months += db_s["duration_months"]
            attached_services_list.append({
                "service_id": str(s.service_id),
                "code": db_s["code"],
                "name": db_s["name"],
                "price": db_s["price"],
                "duration_months": db_s["duration_months"],
            })
    return extra_warranty_months, attached_services_list


class IdempotencyOrderExistsException(Exception):
    def __init__(self, order_id: UUID) -> None:
        self.order_id = order_id


class CreateOrderUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session
        self._shipping_pricing = SandboxShippingPricingService()
        self._momo_gateway = MoMoSandboxGateway()
        self._sepay_gateway = SePayPaymentGateway()
        self._zalopay_gateway = ZaloPaySandboxGateway()

    async def _resolve_checkout_lines(
        self,
        request: CreateOrderRequest,
        *,
        for_update: bool,
    ) -> list[ResolvedCheckoutLine]:
        resolved: list[ResolvedCheckoutLine] = []
        for item in request.items:
            if item.used_device_id:
                if item.attached_services:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Thiết bị cũ không hỗ trợ dịch vụ đi kèm trong luồng này.",
                    )
                if item.quantity != 1:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mỗi thiết bị cũ chỉ được mua với số lượng 1.")
                device = await used_product_repo.get_checkout_device(self._session, item.used_device_id)
                if device is None:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Thiết bị cũ không còn sẵn sàng để bán.")
                unit_price = _checkout_money(device["salePrice"])
                if unit_price != _checkout_money(item.unit_price):
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Giá thiết bị cũ đã thay đổi. Vui lòng tải lại giỏ hàng.")
                resolved.append(
                    ResolvedCheckoutLine(
                        product_id=UUID(str(device["productId"])) if device.get("productId") else None,
                        variant_id=UUID(str(device["variantId"])) if device.get("variantId") else None,
                        used_device_id=item.used_device_id,
                        product_name=str(device.get("title") or item.product_name).strip(),
                        quantity=1,
                        unit_price=unit_price,
                        stock_quantity=1,
                        category_id=UUID(str(device.get("subcategoryId") or device.get("categoryId"))) if (device.get("subcategoryId") or device.get("categoryId")) else None,
                        brand_id=UUID(str(device["brandId"])) if device.get("brandId") else None,
                        imeis=item.imeis,
                        serial_numbers=item.serial_numbers,
                        warranty_months_snapshot=int(device.get("warrantyMonths") or 0),
                    )
                )
                continue

            if item.variant_id:
                inventory_row = await commerce_repo.get_variant_inventory_for_update(
                    self._session,
                    variant_id=item.variant_id,
                    product_id=item.product_id,
                    for_update=for_update,
                )
                if not inventory_row:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy biến thể sản phẩm đang bán.")
                current_price, regular_price, flash_sale_id, sale_quantity = await _resolve_checkout_price(
                    self._session, inventory_row, item.quantity, request.user_id, lock_quota=for_update
                )
                if current_price <= 0 and not request.is_offline:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sản phẩm chưa có giá bán hợp lệ.")
                suffix = _variant_suffix(inventory_row)
                product_name = str(inventory_row["product_name"])
                if suffix:
                    product_name = f"{product_name} ({suffix})"
                extra_warranty, srv_list = await _resolve_attached_services(self._session, item)
                service_unit_price = _checkout_money(sum(Decimal(str(service["price"])) for service in srv_list))
                current_price += service_unit_price
                regular_price += service_unit_price
                if not request.is_offline and current_price != _checkout_money(item.unit_price):
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Giá sản phẩm hoặc dịch vụ đi kèm đã thay đổi. Vui lòng tải lại giỏ hàng.")
                if sale_quantity > 0:
                    resolved.append(
                    ResolvedCheckoutLine(
                        product_id=inventory_row["product_id"],
                        variant_id=item.variant_id,
                        used_device_id=None,
                        product_name=(item.product_name if request.is_offline else product_name),
                        quantity=sale_quantity,
                        unit_price=_checkout_money(item.unit_price) if request.is_offline else current_price,
                        stock_quantity=int(inventory_row["stock_quantity"] or 0),
                        category_id=inventory_row["subcategory_id"] or inventory_row["category_id"],
                        brand_id=inventory_row["brand_id"],
                        imeis=item.imeis,
                        serial_numbers=item.serial_numbers,
                        warranty_months_snapshot=int(inventory_row.get("warranty_months_snapshot") or 0) + extra_warranty,
                        flash_sale_id=None if request.is_offline else flash_sale_id,
                        attached_services=srv_list,
                    )
                )
                regular_quantity = item.quantity - sale_quantity
                if regular_quantity > 0:
                    resolved.append(
                        ResolvedCheckoutLine(
                            product_id=inventory_row["product_id"], variant_id=item.variant_id, used_device_id=None,
                            product_name=product_name, quantity=regular_quantity, unit_price=regular_price,
                            stock_quantity=int(inventory_row["stock_quantity"] or 0),
                            category_id=inventory_row["subcategory_id"] or inventory_row["category_id"],
                            brand_id=inventory_row["brand_id"], imeis=item.imeis, serial_numbers=item.serial_numbers,
                            warranty_months_snapshot=int(inventory_row.get("warranty_months_snapshot") or 0) + extra_warranty,
                            attached_services=srv_list,
                        )
                    )
                continue

            inventory_row = await commerce_repo.get_product_inventory_for_update(
                self._session,
                item.product_id,
                for_update=for_update,
            )
            if not inventory_row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sản phẩm đang bán.")
            current_price, regular_price, flash_sale_id, sale_quantity = await _resolve_checkout_price(
                self._session, inventory_row, item.quantity, request.user_id, lock_quota=for_update
            )
            if current_price <= 0 and not request.is_offline:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sản phẩm chưa có giá bán hợp lệ.")
            extra_warranty, srv_list = await _resolve_attached_services(self._session, item)
            service_unit_price = _checkout_money(sum(Decimal(str(service["price"])) for service in srv_list))
            current_price += service_unit_price
            regular_price += service_unit_price
            if not request.is_offline and current_price != _checkout_money(item.unit_price):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Giá sản phẩm hoặc dịch vụ đi kèm đã thay đổi. Vui lòng tải lại giỏ hàng.")
            if sale_quantity > 0:
                resolved.append(
                ResolvedCheckoutLine(
                    product_id=item.product_id,
                    variant_id=None,
                    used_device_id=None,
                    product_name=(item.product_name if request.is_offline else str(inventory_row["product_name"])),
                    quantity=sale_quantity,
                    unit_price=_checkout_money(item.unit_price) if request.is_offline else current_price,
                    stock_quantity=int(inventory_row["stock_quantity"] or 0),
                    category_id=inventory_row["subcategory_id"] or inventory_row["category_id"],
                    brand_id=inventory_row["brand_id"],
                    imeis=item.imeis,
                    serial_numbers=item.serial_numbers,
                    warranty_months_snapshot=int(inventory_row.get("warranty_months_snapshot") or 0) + extra_warranty,
                    flash_sale_id=None if request.is_offline else flash_sale_id,
                    attached_services=srv_list,
                )
            )
            regular_quantity = item.quantity - sale_quantity
            if regular_quantity > 0:
                resolved.append(
                    ResolvedCheckoutLine(
                        product_id=item.product_id, variant_id=None, used_device_id=None,
                        product_name=str(inventory_row["product_name"]), quantity=regular_quantity,
                        unit_price=regular_price, stock_quantity=int(inventory_row["stock_quantity"] or 0),
                        category_id=inventory_row["subcategory_id"] or inventory_row["category_id"],
                        brand_id=inventory_row["brand_id"], imeis=item.imeis, serial_numbers=item.serial_numbers,
                        warranty_months_snapshot=int(inventory_row.get("warranty_months_snapshot") or 0) + extra_warranty,
                        attached_services=srv_list,
                    )
                )
        return resolved

    @connection_retry_on_deadlock(max_retries=3, backoff_seconds=0.2)
    async def execute(self, request: CreateOrderRequest) -> CreateOrderResponse:
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

        preview_lines = await self._resolve_checkout_lines(request, for_update=False)
        subtotal = sum(line.unit_price * line.quantity for line in preview_lines)
        shipping_quote = await self._shipping_pricing.quote(
            self._session,
            shipping_address=request.shipping.shipping_address,
            subtotal_amount=subtotal,
            item_count=sum(line.quantity for line in preview_lines),
            provider=request.shipping.provider or "MOCK_GHN",
            lat=request.shipping.lat,
            lng=request.shipping.lng,
        )
        shipping_fee = _pos_shipping_fee(request, shipping_quote.fee)

        voucher_discount = Decimal("0")
        wallet_claim_id: UUID | None = None
        checkout_url = None
        payment_transaction_id = None
        payment_expires_at = None
        provider_order_id = None
        total = Decimal("0")
        earned_points = 0
        order = None
        await self._session.rollback()

        try:
            async with self._session.begin():
                if request.idempotency_key:
                    existing = await commerce_repo.get_order_by_idempotency_key(self._session, request.idempotency_key)
                    if existing is not None:
                        raise IdempotencyOrderExistsException(existing.id)

                resolved_lines = await self._resolve_checkout_lines(request, for_update=True)
                subtotal = sum(line.unit_price * line.quantity for line in resolved_lines)
                user = None
                if request.user_id:
                    user = await commerce_repo.get_user_for_update(self._session, request.user_id)
                    if user is None:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài khoản.")
                    from app.application.services.loyalty_maintenance_service import expire_user_points
                    synced_balance = await expire_user_points(self._session, user_id=user.id)
                    if synced_balance is not None:
                        user.loyalty_points_balance = synced_balance
                    if user.status != "ACTIVE":
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản của bạn hiện đang bị khóa hoặc ngưng hoạt động.")
                    if user.loyalty_wallet_status != "ACTIVE":
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ví điểm thưởng không ở trạng thái hoạt động.")
                    if request.loyalty_points_used > user.loyalty_points_balance:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Không đủ điểm thưởng.")

                product_ids = {str(line.product_id) for line in resolved_lines if line.product_id}
                category_ids = {str(line.category_id) for line in resolved_lines if line.category_id}
                brand_ids = {str(line.brand_id) for line in resolved_lines if line.brand_id}

                voucher = None
                voucher_service = VoucherService(session=self._session)
                if request.voucher_code:
                    voucher = await commerce_repo.get_active_voucher_for_update(self._session, request.voucher_code)
                    if voucher is None:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail={
                                "code": "VOUCHER_ERR_INVALID",
                                "message": "Voucher không hợp lệ hoặc không còn hoạt động.",
                                "metadata": {},
                            },
                        )
                    validation = await voucher_service.validate_for_order(
                        voucher=voucher,
                        request=request,
                        lines=resolved_lines,
                        user=user,
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
                total = max(Decimal("0"), subtotal - voucher_discount - points_discount + shipping_fee)
                _validate_pos_cash_received(request, total)
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
                used_device_ids: set[UUID] = set()
                for line in resolved_lines:
                    if line.used_device_id:
                        if line.used_device_id in used_device_ids:
                            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiết bị cũ bị trùng trong giỏ hàng.")
                        used_device_ids.add(line.used_device_id)
                        continue
                    if line.variant_id:
                        old_quantity = line.stock_quantity
                        reserved_quantity = await commerce_repo.get_active_reserved_quantity(
                            self._session,
                            product_id=None,
                            variant_id=line.variant_id,
                        )
                        reservation_key = ("variant", line.variant_id)
                        already_requested = int(reservation_lines.get(reservation_key, {}).get("quantity", 0))
                        if old_quantity - reserved_quantity - already_requested - line.quantity < 0:
                            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Không đủ tồn kho cho {line.product_name}.")
                        reservation_lines[reservation_key] = {
                            "product_id": line.product_id,
                            "variant_id": line.variant_id,
                            "quantity": already_requested + line.quantity,
                        }
                    elif line.product_id:
                        old_quantity = line.stock_quantity
                        reserved_quantity = await commerce_repo.get_active_reserved_quantity(
                            self._session,
                            product_id=line.product_id,
                            variant_id=None,
                        )
                        reservation_key = ("product", line.product_id)
                        already_requested = int(reservation_lines.get(reservation_key, {}).get("quantity", 0))
                        if old_quantity - reserved_quantity - already_requested - line.quantity < 0:
                            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Không đủ tồn kho cho {line.product_name}.")
                        reservation_lines[reservation_key] = {
                            "product_id": line.product_id,
                            "variant_id": None,
                            "quantity": already_requested + line.quantity,
                        }

                flash_sale_quantities: dict[UUID, int] = {}
                for line in resolved_lines:
                    if line.flash_sale_id is None:
                        continue
                    flash_sale_quantities[line.flash_sale_id] = flash_sale_quantities.get(line.flash_sale_id, 0) + line.quantity
                for sale_id, quantity in flash_sale_quantities.items():
                    reserved = await flash_sale_repo.reserve_flash_sale_quantity(
                        self._session,
                        sale_id=sale_id,
                        quantity=quantity,
                    )
                    if reserved is None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Số lượng flash sale vừa hết. Vui lòng tải lại giỏ hàng để cập nhật giá.",
                        )

                order = Order(
                    id=order_id,
                    user_id=request.user_id,
                    order_code=order_code,
                    status="COMPLETED" if request.is_offline else ("PAID" if total == 0 else "PENDING"),
                    payment_method=request.payment_method,
                    payment_status="PAID" if (request.is_offline or total == 0) else ("UNPAID" if request.payment_method == "COD" else "PENDING"),
                    subtotal_amount=subtotal,
                    discount_amount=voucher_discount + points_discount,
                    voucher_discount_amount=voucher_discount,
                    loyalty_discount_amount=points_discount,
                    shipping_fee=shipping_fee,
                    shipping_provider=None if request.is_offline else (request.shipping.provider or shipping_quote.provider),
                    total_amount=total,
                    loyalty_points_earned=earned_points,
                    loyalty_points_used=request.loyalty_points_used,
                    voucher_code=voucher.code if voucher else None,
                    voucher_claim_id=None,
                    voucher_device_id=request.voucher_device_id,
                    voucher_ip_address=request.voucher_ip_address,
                    idempotency_key=request.idempotency_key,
                    recipient_name=request.shipping.recipient_name,
                    recipient_phone=request.shipping.recipient_phone,
                    recipient_email=request.shipping.recipient_email,
                    shipping_address=request.shipping.shipping_address,
                    internal_note=f"[POS] {request.internal_note or ''}".strip() if request.is_offline else None,
                    fulfillment_method="STORE_PICKUP" if request.is_offline else "DELIVERY",
                    completed_at=datetime.now(timezone.utc) if request.is_offline else None,
                )
                commerce_repo.save_model(self._session, order)
                await self._session.flush()

                if voucher is not None:
                    claimed_voucher = await voucher_service.mark_voucher_used(
                        voucher=voucher,
                        order_id=order_id,
                        discount_amount=voucher_discount,
                        user_id=request.user_id,
                        reserve_only=not (request.is_offline or total == 0),
                        device_id=request.voucher_device_id,
                        ip_address=request.voucher_ip_address,
                    )
                    wallet_claim_id = claimed_voucher.id if claimed_voucher else None
                    if wallet_claim_id:
                        order.voucher_claim_id = wallet_claim_id
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
                reserved_used_devices: dict[UUID, dict] = {}
                for device_id in used_device_ids:
                    reserved_device = await used_product_repo.reserve_device_for_order(
                        self._session,
                        device_id=device_id,
                        order_id=order.id,
                        order_code=order.order_code,
                    )
                    if reserved_device is None:
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Thiết bị cũ không còn sẵn sàng để bán.")
                    sale_price = Decimal(str(reserved_device["salePrice"] or 0))
                    line = next(resolved_line for resolved_line in resolved_lines if resolved_line.used_device_id == device_id)
                    if _checkout_money(sale_price) != line.unit_price:
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Giá thiết bị cũ đã thay đổi. Vui lòng tải lại giỏ hàng.")
                    reserved_used_devices[device_id] = reserved_device
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
                for line in resolved_lines:
                    order_item_id = uuid4()
                    commerce_repo.save_model(
                        self._session,
                        OrderItem(
                            id=order_item_id,
                            order_id=order.id,
                            product_id=None if line.used_device_id else line.product_id,
                            variant_id=None if line.used_device_id else line.variant_id,
                            used_device_id=line.used_device_id,
                            product_name=line.product_name,
                            quantity=line.quantity,
                            unit_price=line.unit_price,
                            total_price=line.unit_price * line.quantity,
                            flash_sale_id=line.flash_sale_id,
                            flash_sale_quantity=line.quantity if line.flash_sale_id else 0,
                            warranty_months_snapshot=line.warranty_months_snapshot,
                            attached_services=line.attached_services,
                        ),
                    )
                    if request.is_offline:
                        pos_issue_allocations.append(
                            {
                                "order_item_id": order_item_id,
                                "imeis": line.imeis,
                                "serial_numbers": line.serial_numbers,
                            }
                        )

                if request.is_offline:
                    # Bắt buộc flush dòng đơn trước khi use case xuất kho truy vấn lại bằng SQL.
                    await self._session.flush()

                    # Trừ kho thực tế bằng FIFO
                    complete_use_case = CompleteOrderUseCase(session=self._session)
                    await complete_use_case._ship_order_items(order, issue_allocations=pos_issue_allocations)

                    # Đóng các reservations vừa tạo dưới dạng CONSUMED
                    await commerce_repo.close_active_order_reservations(
                        self._session,
                        order_id=order.id,
                        status="CONSUMED",
                    )

                    # Cộng điểm và ghi nhận doanh số xét hạng ngay cho đơn offline.
                    if user:
                        from app.application.services.loyalty_maintenance_service import upgrade_tier_after_order
                        balance_before = user.loyalty_points_balance
                        user.loyalty_points_balance += earned_points
                        await upgrade_tier_after_order(
                            self._session,
                            user=user,
                            order_id=order.id,
                            order_amount=order.total_amount,
                        )
                        if earned_points > 0:
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

                if not request.is_offline and request.payment_method != "COD":
                    if request.payment_method not in {"MOMO", "ZALOPAY", "SEPAY"}:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Hiện hệ thống chỉ hỗ trợ COD, MoMo Sandbox, ZaloPay Sandbox và SePay Sandbox.",
                        )
                    payment_transaction_id = uuid4()
                    if total == 0:
                        payment_expires_at = None
                        provider_order_id = f"{order.order_code}-0"
                        checkout_url = "INTERNAL_0_VND"
                        commerce_repo.save_model(
                            self._session,
                            PaymentTransaction(
                                id=payment_transaction_id,
                                order_id=order.id,
                                provider=request.payment_method,
                                amount=total,
                                status="PAID",
                                transaction_ref=provider_order_id,
                                checkout_url=checkout_url,
                                attempt_number=1,
                                expires_at=None,
                                paid_at=datetime.now(timezone.utc),
                                raw_response={"message": "Thanh toán thành công đơn hàng 0đ qua hệ thống điểm/voucher."},
                            ),
                        )
                        from app.application.services.inventory_service import create_outbound_document_from_order
                        await create_outbound_document_from_order(self._session, order.id)
                    else:
                        timeout_minutes_by_provider = {
                            "MOMO": settings.momo_payment_timeout_minutes,
                            "ZALOPAY": settings.zalopay_payment_timeout_minutes,
                            "SEPAY": settings.sepay_payment_timeout_minutes,
                        }
                        timeout_minutes = timeout_minutes_by_provider[request.payment_method]
                        payment_expires_at = datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
                        if request.payment_method == "MOMO":
                            provider_order_id = f"{order.order_code}-1"
                        elif request.payment_method == "ZALOPAY":
                            vietnam_date = datetime.now(timezone(timedelta(hours=7))).strftime("%y%m%d")
                            provider_order_id = f"{vietnam_date}_{order.order_code[-10:]}01"
                        else:
                            provider_order_id = f"{order.order_code}-1"

                        # Lưu PaymentTransaction trống trước (chưa có checkout_url và raw_response)
                        commerce_repo.save_model(
                            self._session,
                            PaymentTransaction(
                                id=payment_transaction_id,
                                order_id=order.id,
                                provider=request.payment_method,
                                amount=total,
                                status="PENDING",
                                transaction_ref=provider_order_id,
                                checkout_url=None,
                                attempt_number=1,
                                expires_at=payment_expires_at,
                                raw_response={},
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
                            reason="Dùng điểm thưởng khi thanh toán đơn hàng.",
                            metadata_json={"order_code": order.order_code},
                        ),
                    )
                    commerce_repo.save_model(self._session, user)
        except IdempotencyOrderExistsException as e:
            await self._session.rollback()
            existing_id = e.order_id
            existing = await self._session.get(Order, existing_id)
            if existing is None:
                raise HTTPException(status_code=500, detail="Không tìm thấy đơn hàng trùng lặp.")
            latest_payment = await commerce_repo.get_latest_payment_transaction(self._session, existing_id)
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
            return response

        # Ngoài transaction chính: gọi gateway thanh toán
        if not request.is_offline and request.payment_method != "COD" and total > 0:
            try:
                payment_init = None
                if request.payment_method == "MOMO":
                    payment_init = await self._momo_gateway.create_payment(
                        order_code=provider_order_id,
                        amount=total,
                        order_info=f"Thanh toán đơn hàng {order.order_code}",
                        extra_data={"orderCode": order.order_code, "userId": str(request.user_id) if request.user_id else ""},
                        request_id=str(payment_transaction_id),
                    )
                elif request.payment_method == "ZALOPAY":
                    payment_init = await self._zalopay_gateway.create_payment(
                        app_trans_id=provider_order_id,
                        amount=total,
                        app_user=str(request.user_id or "electromart-sandbox"),
                        description=f"ElectroMart Sandbox - Thanh toán đơn hàng {order.order_code}",
                        callback_url=settings.zalopay_callback_url,
                        redirect_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_transaction_id}",
                    )
                else:
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
            except Exception as e:
                # Saga Compensation: Hủy đơn hàng và rollback các tài nguyên đã commit trong Transaction 1
                async with self._session.begin():
                    complete_use_case = CompleteOrderUseCase(session=self._session)
                    await complete_use_case.execute(
                        order_id=order.id,
                        status_value="PAYMENT_FAILED",
                        cancellation_reason=f"Khởi tạo giao dịch thanh toán thất bại: {str(e)}",
                        changed_by="system-payment-init-failed",
                    )
                if isinstance(e, HTTPException):
                    raise e
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Không thể kết nối đến cổng thanh toán {request.payment_method}. Chi tiết: {str(e)}"
                )

            # Giao dịch 2: Cập nhật kết quả khởi tạo thành công vào PaymentTransaction
            async with self._session.begin():
                payment_tx = await commerce_repo.get_payment_transaction(self._session, payment_transaction_id)
                if payment_tx:
                    payment_tx.checkout_url = checkout_url
                    payment_tx.raw_response = (payment_init.raw_response if payment_init else {"mode": "sandbox"})
                    commerce_repo.save_model(self._session, payment_tx)

        return CreateOrderResponse(
            order_id=order.id,
            order_code=order.order_code,
            payment_method=order.payment_method,
            payment_status=order.payment_status,
            shipping_fee=Decimal(order.shipping_fee or 0),
            total_amount=total,
            loyalty_points_earned=earned_points,
            checkout_url=checkout_url,
            payment_transaction_id=payment_transaction_id,
            payment_expires_at=payment_expires_at.isoformat() if payment_expires_at else None,
        )

    async def _existing_checkout_url(self, order_id: UUID) -> str | None:
        return await commerce_repo.get_checkout_url(self._session, order_id)
