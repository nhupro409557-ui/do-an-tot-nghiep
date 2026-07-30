from .common import *
from app.infrastructure.database.repositories import voucher_repo
from typing import Any
from app.application.commerce.schemas import VoucherItemPayload

class VoucherDomainError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, metadata: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.metadata = metadata or {}

def raise_voucher_error(code: str, message: str, status_code: int = 400, metadata: dict | None = None):
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "metadata": metadata or {}},
    )

VOUCHER_RULE_PIPELINE: tuple[VoucherRule, ...] = (
    VoucherActiveWindowRule(),   # 1. Hiệu lực thời gian
    VoucherWalletRule(),         # 2. Quyền sở hữu / trạng thái ví
    MinOrderRule(),              # 3. Giá trị đơn hợp lệ
    ChannelPaymentRule(),        # 4. Kênh và phương thức thanh toán
    UsageLimitRule(),            # 5. Quota lượt dùng
    BudgetRule(),                # 6. Ngân sách chiến dịch
    AudienceRule(),              # 7. Người dùng / hạng thành viên
    FirstOrderRule(),            # 8. Lịch sử đơn hàng
    AbandonedCartRule(),         # 9. Ngữ cảnh chiến dịch
    IdentityLimitRule(),         # 10. Per-user/device/IP
    TargetingRule(),             # 11. Product/category/brand scope
)


class VoucherService:
    # Rule pipeline keeps the voucher rules modular so future business rules can be added safely.
    _rules: tuple[VoucherRule, ...] = VOUCHER_RULE_PIPELINE

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def validate_for_order(
        self,
        *,
        voucher: Any,
        request: Any,
        lines: list,
        user: Any,
    ) -> VoucherValidationResponse:
        if not request.payment_method:
            raise_voucher_error("VOUCHER_ERR_PAYMENT_METHOD_REQUIRED", "Thiếu phương thức thanh toán.", 400)

        items = [
            VoucherItemPayload(
                productId=str(line.product_id),
                categoryId=str(line.category_id) if line.category_id else None,
                brandId=str(line.brand_id) if line.brand_id else None,
                price=line.unit_price,
                quantity=line.quantity,
                isFlashSale=line.flash_sale_id is not None,
            )
            for line in lines
            if line.product_id
        ]

        return await self.validate(
            code=voucher.code,
            subtotal_amount=sum(line.unit_price * line.quantity for line in lines),
            user_id=request.user_id,
            user_tier=user.loyalty_tier if user else None,
            device_id=request.voucher_device_id,
            ip_address=request.voucher_ip_address,
            payment_method=request.payment_method,
            channel="WEB",
            items=items,
            voucher=voucher,
        )

    async def validate(
        self,
        *,
        code: str,
        subtotal_amount: Decimal,
        user_id: UUID | None = None,
        user_tier: str | None = None,
        abandoned_cart_recovery: bool = False,
        device_id: str | None = None,
        ip_address: str | None = None,
        payment_method: str | None = None,
        channel: str | None = None,
        product_ids: set[str] | None = None,
        category_ids: set[str] | None = None,
        brand_ids: set[str] | None = None,
        items: list | None = None,
        voucher: Any | None = None,
    ) -> VoucherValidationResponse:
        if items:
            product_ids_to_fetch = []
            for item in items:
                pid = getattr(item, "productId", getattr(item, "product_id", None))
                if pid:
                    try:
                        product_ids_to_fetch.append(UUID(str(pid)))
                    except ValueError:
                        continue
            
            prod_map = await commerce_repo.get_products_category_and_brand_map(self._session, product_ids_to_fetch)
            
            for item in items:
                pid = getattr(item, "productId", getattr(item, "product_id", None))
                try:
                    uuid_pid = UUID(str(pid)) if pid else None
                except ValueError:
                    uuid_pid = None
                if not uuid_pid or uuid_pid not in prod_map:
                    return self._invalid(code.upper(), "VOUCHER_ERR_PRODUCT_NOT_FOUND", "Sản phẩm không hợp lệ.")
                cat_set, brand_id, coalesce_cat_id = prod_map[uuid_pid]
                item.categoryId = coalesce_cat_id
                item.brandId = brand_id
            
            product_ids = {str(uuid_pid) for uuid_pid in prod_map.keys()}
            category_ids = {
                cat_id
                for cat_set, _brand_id, _coalesce_id in prod_map.values()
                for cat_id in cat_set
            }
            brand_ids = {
                brand_id
                for _cat_set, brand_id, _coalesce_id in prod_map.values()
                if brand_id
            }
        elif product_ids:
            product_ids_to_fetch = []
            for pid in product_ids:
                try:
                    product_ids_to_fetch.append(UUID(str(pid)))
                except ValueError:
                    continue
            prod_map = await commerce_repo.get_products_category_and_brand_map(self._session, product_ids_to_fetch)
            product_ids = {str(uuid_pid) for uuid_pid in prod_map.keys()}
            category_ids = {
                cat_id
                for cat_set, _brand_id, _coalesce_id in prod_map.values()
                for cat_id in cat_set
            }
            brand_ids = {
                brand_id
                for _cat_set, brand_id, _coalesce_id in prod_map.values()
                if brand_id
            }
        else:
            product_ids = set()
            category_ids = set()
            brand_ids = set()

        if voucher is None:
            voucher = await self._get_active_voucher(code)
        if voucher is None:
            return self._invalid(code.upper(), "VOUCHER_ERR_INVALID", "Voucher không hợp lệ hoặc không còn hoạt động.")

        # Acquire advisory locks for identity scope during validation to prevent TOCTOU within the same transaction scope
        await self._lock_voucher_identity_scope(
            voucher_id=voucher.id,
            user_id=user_id,
            device_id=device_id,
            ip_address=ip_address,
        )

        now = await commerce_repo.get_database_now(self._session)

        # Tính toán eligible_subtotal thực tế áp dụng của voucher (bao gồm loại trừ Flash Sale và Targeting)
        eligible_subtotal = subtotal_amount
        if items:
            include_products = set(voucher.include_product_ids if isinstance(voucher.include_product_ids, list) else [])
            exclude_products = set(voucher.exclude_product_ids if isinstance(voucher.exclude_product_ids, list) else [])
            include_categories = set(voucher.include_category_ids if isinstance(voucher.include_category_ids, list) else [])
            exclude_categories = set(voucher.exclude_category_ids if isinstance(voucher.exclude_category_ids, list) else [])
            include_brands = set(voucher.include_brand_ids if isinstance(voucher.include_brand_ids, list) else [])
            exclude_brands = set(voucher.exclude_brand_ids if isinstance(voucher.exclude_brand_ids, list) else [])

            eligible_sum = Decimal("0")
            for item in items:
                pid = getattr(item, "productId", getattr(item, "product_id", None))
                pid = str(pid) if pid is not None else ""

                cid = getattr(item, "categoryId", getattr(item, "category_id", None))
                cid = str(cid) if cid is not None else ""

                bid = getattr(item, "brandId", getattr(item, "brand_id", None))
                bid = str(bid) if bid is not None else ""

                price = Decimal(str(getattr(item, "price", 0)))
                qty = int(getattr(item, "quantity", 1))

                is_flash_sale = bool(getattr(item, "isFlashSale", getattr(item, "is_flash_sale", False)))

                # Không cho phép cộng dồn voucher nếu voucher không stackable và sản phẩm đang Flash Sale
                if not voucher.stackable and is_flash_sale:
                    continue

                try:
                    uuid_pid = UUID(str(pid)) if pid else None
                except ValueError:
                    uuid_pid = None

                if uuid_pid and uuid_pid in prod_map:
                    cat_set, _, _ = prod_map[uuid_pid]
                    item_category_ids = cat_set
                else:
                    item_category_ids = {cid} if cid else set()

                is_valid = True
                if include_products and pid not in include_products and not voucher.apply_outside_scope:
                    is_valid = False
                if exclude_products and pid in exclude_products:
                    is_valid = False
                if include_categories and not item_category_ids.intersection(include_categories) and not voucher.apply_outside_scope:
                    is_valid = False
                if exclude_categories and item_category_ids.intersection(exclude_categories):
                    is_valid = False
                if include_brands and bid not in include_brands and not voucher.apply_outside_scope:
                    is_valid = False
                if exclude_brands and bid in exclude_brands:
                    is_valid = False

                if is_valid:
                    eligible_sum += price * qty
            eligible_subtotal = eligible_sum

        context = VoucherValidationContext(
            voucher=voucher,
            now=now,
            subtotal_amount=subtotal_amount,
            user_id=user_id,
            user_tier=user_tier,
            abandoned_cart_recovery=abandoned_cart_recovery,
            device_id=device_id,
            ip_address=ip_address,
            payment_method=payment_method,
            channel=channel,
            product_ids=product_ids or set(),
            category_ids=category_ids or set(),
            brand_ids=brand_ids or set(),
            items=items or [],
            eligible_subtotal=eligible_subtotal,
        )
        for rule in self._rules:
            failure = await rule.check(self, context)
            if failure is not None:
                return failure

        discount = self._calculate_discount(voucher=voucher, subtotal_amount=subtotal_amount, context=context)
        if voucher.total_budget_cap is not None:
            remaining_budget = Decimal(voucher.total_budget_cap) - Decimal(voucher.total_discount_used or 0)
            if remaining_budget <= 0:
                return self._invalid(
                    voucher.code,
                    "VOUCHER_ERR_BUDGET",
                    "Ngân sách chiến dịch voucher đã được dùng hết.",
                    {"budget_cap": str(voucher.total_budget_cap), "used_budget": str(voucher.total_discount_used or 0)},
                )
            discount = min(discount, remaining_budget)
        return VoucherValidationResponse(
            code=voucher.code,
            valid=True,
            discount_amount=discount,
            message="Áp dụng voucher thành công.",
            error_code=None,
            metadata={
                "stackable": bool(voucher.stackable),
                "wallet_claim_required": voucher.validity_days_after_claim > 0,
                "claimed_voucher_id": str(context.claimed_voucher.id) if context.claimed_voucher else None,
            },
        )

    async def claim_voucher(self, *, user_id: UUID, voucher_id: UUID) -> UserVoucherResponse:
        now = datetime.now(timezone.utc)
        voucher = await commerce_repo.get_voucher_by_id_for_update(self._session, voucher_id)
        if voucher is None:
            raise_voucher_error("VOUCHER_ERR_NOT_FOUND", "Không tìm thấy voucher.", 404)
        if voucher.status != "ACTIVE":
            raise_voucher_error("VOUCHER_ERR_INACTIVE", "Voucher không ở trạng thái hoạt động.", 400)
        if voucher.ends_at and voucher.ends_at < now:
            raise_voucher_error("VOUCHER_ERR_EXPIRED", "Voucher đã hết hạn.", 400, {"ends_at": voucher.ends_at.isoformat()})
        if voucher.usage_limit > 0 and voucher.used_count >= voucher.usage_limit:
            raise_voucher_error("VOUCHER_ERR_USAGE_LIMIT", "Voucher đã hết lượt sử dụng.", 400, {"usage_limit": voucher.usage_limit, "used_count": voucher.used_count})
        if voucher.starts_at and voucher.starts_at > now:
            raise_voucher_error("VOUCHER_ERR_NOT_STARTED", "Voucher chưa đến thời gian áp dụng.", 400, {"starts_at": voucher.starts_at.isoformat()})

        if voucher.audience_type == "SPECIFIC_USER":
            if voucher.assigned_user_id and voucher.assigned_user_id != user_id:
                raise_voucher_error("VOUCHER_ERR_ASSIGNED_USER", "Voucher này không dành cho tài khoản của bạn.", 400)
            if not await commerce_repo.has_user_voucher_assignment(self._session, user_id=user_id, voucher_id=voucher_id):
                raise_voucher_error("VOUCHER_ERR_ASSIGNED_USER", "Voucher này không dành cho tài khoản của bạn.", 400)

        if voucher.first_order_only:
            orders_count = await self._user_order_count(user_id)
            if orders_count > 0:
                raise_voucher_error("VOUCHER_ERR_FIRST_ORDER_ONLY", "Voucher chỉ áp dụng cho khách hàng chưa có đơn hàng nào.", 400)

        existing = await commerce_repo.get_existing_user_voucher(self._session, user_id=user_id, voucher_id=voucher_id)
        if existing is not None:
            return self._wallet_response(existing, voucher)

        redemption_points = int(voucher.redemption_points or 0)
        if redemption_points > 0:
            user = await commerce_repo.get_user_for_update(self._session, user_id)
            if user is None:
                raise_voucher_error("VOUCHER_ERR_USER_NOT_FOUND", "Không tìm thấy tài khoản.", 404)
            if user.loyalty_wallet_status != "ACTIVE":
                raise_voucher_error("VOUCHER_ERR_WALLET_CLOSED", "Ví điểm thưởng không ở trạng thái hoạt động.", 409)
            balance_before = int(user.loyalty_points_balance or 0)
            if balance_before < redemption_points:
                raise_voucher_error(
                    "VOUCHER_ERR_INSUFFICIENT_POINTS",
                    "Bạn không đủ điểm để đổi voucher này.",
                    400,
                    {"required_points": redemption_points, "current_points": balance_before},
                )
            balance_after = balance_before - redemption_points
            user.loyalty_points_balance = balance_after
            commerce_repo.save_model(self._session, user)
            commerce_repo.save_model(
                self._session,
                LoyaltyTransaction(
                    id=uuid4(),
                    user_id=user_id,
                    order_id=None,
                    type=LoyaltyTransactionType.REDEEM.value,
                    points=redemption_points,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    reason=f"Đổi voucher {voucher.code}",
                    metadata_json={
                        "source": "voucher_redemption",
                        "voucherId": str(voucher.id),
                        "voucherCode": voucher.code,
                    },
                ),
            )

        expires_at = None
        if voucher.validity_days_after_claim > 0:
            expires_at = now + timedelta(days=voucher.validity_days_after_claim)
        wallet_voucher = UserVoucher(
            id=uuid4(),
            user_id=user_id,
            voucher_id=voucher_id,
            status="AVAILABLE",
            claimed_at=now,
            expires_at=expires_at,
        )
        await commerce_repo.add_user_voucher(self._session, wallet_voucher)
        return self._wallet_response(wallet_voucher, voucher)

    async def list_user_vouchers(self, *, user_id: UUID) -> list[UserVoucherResponse]:
        rows = await commerce_repo.list_user_vouchers_with_voucher(self._session, user_id)
        now = datetime.now(timezone.utc)
        responses: list[UserVoucherResponse] = []
        for wallet_voucher, voucher in rows:
            effective_expiry = wallet_voucher.expires_at or voucher.ends_at
            if wallet_voucher.status != "AVAILABLE":
                continue
            if voucher.status != "ACTIVE" or (voucher.starts_at and voucher.starts_at > now):
                continue
            if effective_expiry and effective_expiry <= now:
                await self._expire_wallet_voucher(wallet_voucher)
                continue
            if voucher.usage_limit > 0 and voucher.used_count >= voucher.usage_limit:
                continue
            if voucher.total_budget_cap is not None and voucher.total_discount_used >= voucher.total_budget_cap:
                continue
            responses.append(self._wallet_response(wallet_voucher, voucher))
        return responses

    async def _lock_voucher_identity_scope(
        self,
        *,
        voucher_id: UUID,
        user_id: UUID | None,
        device_id: str | None,
        ip_address: str | None,
    ) -> None:
        keys = [f"voucher:{voucher_id}:quota"]
        if user_id:
            keys.append(f"voucher:{voucher_id}:user:{user_id}")
        if device_id:
            keys.append(f"voucher:{voucher_id}:device:{device_id}")
        if ip_address:
            keys.append(f"voucher:{voucher_id}:ip:{ip_address}")

        for key in keys:
            await self._session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": key},
            )

    async def mark_voucher_used(
        self,
        *,
        voucher: Voucher,
        order_id: UUID,
        discount_amount: Decimal,
        user_id: UUID | None,
        reserve_only: bool = True,
        device_id: str | None = None,
        ip_address: str | None = None,
    ) -> UserVoucher | None:
        await self._lock_voucher_identity_scope(
            voucher_id=voucher.id,
            user_id=user_id,
            device_id=device_id,
            ip_address=ip_address,
        )
        claimed_voucher = None

        if voucher.validity_days_after_claim > 0 and user_id:
            claimed_voucher = await commerce_repo.get_claimed_voucher_for_update(
                self._session,
                user_id=user_id,
                voucher_id=voucher.id,
            )
            if claimed_voucher is None:
                raise_voucher_error(
                    "VOUCHER_ERR_WALLET_UNAVAILABLE",
                    "Voucher trong ví không còn khả dụng để giữ cho đơn hàng này.",
                    status.HTTP_409_CONFLICT,
                )

        success = await commerce_repo.increment_voucher_usage_atomic(
            self._session,
            voucher_id=voucher.id,
            discount_amount=discount_amount
        )
        if not success:
            fresh = await commerce_repo.get_voucher_by_id(self._session, voucher.id)
            if fresh:
                if fresh.usage_limit > 0 and fresh.used_count >= fresh.usage_limit:
                    raise_voucher_error(
                        "VOUCHER_ERR_USAGE_LIMIT",
                        "Voucher đã đạt giới hạn lượt sử dụng.",
                        status.HTTP_409_CONFLICT,
                        {"usage_limit": fresh.usage_limit, "used_count": fresh.used_count},
                    )
                if fresh.total_budget_cap is not None:
                    remaining_budget = Decimal(fresh.total_budget_cap) - Decimal(fresh.total_discount_used or 0)
                    if remaining_budget < discount_amount:
                        raise_voucher_error(
                            "VOUCHER_ERR_BUDGET",
                            "Ngân sách chiến dịch voucher không còn đủ cho đơn hàng này.",
                            status.HTTP_409_CONFLICT,
                            {"budget_cap": str(fresh.total_budget_cap), "used_budget": str(fresh.total_discount_used or 0)},
                        )
            raise_voucher_error(
                "VOUCHER_ERR_LIMIT_EXCEEDED",
                "Voucher đã hết lượt sử dụng hoặc vượt quá giới hạn ngân sách chiến dịch.",
                status.HTTP_409_CONFLICT,
            )

        if claimed_voucher is not None:
            claimed_voucher.status = "RESERVED" if reserve_only else "USED"
            claimed_voucher.used_at = None if reserve_only else datetime.now(timezone.utc)
            claimed_voucher.order_id = order_id
            commerce_repo.save_model(self._session, claimed_voucher)

        from sqlalchemy.exc import IntegrityError
        try:
            await commerce_repo.upsert_voucher_usage(
                self._session,
                id=uuid4(),
                order_id=order_id,
                voucher_id=voucher.id,
                user_id=user_id,
                discount_amount=discount_amount,
                status="RESERVED" if reserve_only else "USED",
                device_id=device_id,
                ip_address=ip_address,
            )
        except IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "VOUCHER_ERR_IDENTITY_LIMIT",
                    "message": "Voucher đã đạt giới hạn sử dụng cho người dùng/thiết bị/IP này.",
                    "metadata": {},
                },
            ) from exc

        return claimed_voucher

    async def confirm_voucher_usage(self, *, order: Order) -> None:
        usage = await commerce_repo.get_reserved_voucher_usage(self._session, order.id)
        if usage is not None:
            usage.status = "USED"
            usage.updated_at = datetime.now(timezone.utc)
            await commerce_repo.save_voucher_usage(self._session, usage)
        elif order.voucher_code:
            # Tự động ghi sổ cái ledger mới nếu chưa tồn tại (để bảo toàn tính nhất quán)
            voucher = await commerce_repo.get_active_voucher(self._session, order.voucher_code)
            if voucher:
                await commerce_repo.upsert_voucher_usage(
                    self._session,
                    id=uuid4(),
                    order_id=order.id,
                    voucher_id=voucher.id,
                    user_id=order.user_id,
                    discount_amount=order.voucher_discount_amount or Decimal("0"),
                    status="USED",
                )

        if not order.voucher_claim_id:
            return
        wallet_voucher = await commerce_repo.get_user_voucher_for_update(self._session, order.voucher_claim_id)
        if wallet_voucher is None or wallet_voucher.status == "USED":
            return
        if wallet_voucher.status != "RESERVED" or wallet_voucher.order_id != order.id:
            raise_voucher_error(
                "VOUCHER_ERR_WALLET_STATUS_MISMATCH",
                "Trạng thái voucher trong ví không khớp với đơn hàng cần xác nhận.",
                status.HTTP_409_CONFLICT,
                {"wallet_status": wallet_voucher.status, "order_id": str(wallet_voucher.order_id) if wallet_voucher.order_id else None},
            )
        wallet_voucher.status = "USED"
        wallet_voucher.used_at = datetime.now(timezone.utc)
        commerce_repo.save_model(self._session, wallet_voucher)

    async def rollback_voucher_usage(self, *, order: Order) -> None:
        if not order.voucher_code:
            return

        usage = await commerce_repo.get_voucher_usage_for_update(self._session, order.id)

        if usage is not None and usage.status == "RELEASED":
            return

        # Chỉ lấy voucher_by_order_code_for_update 1 lần duy nhất để tối ưu hóa hiệu năng
        voucher = await commerce_repo.get_voucher_by_order_code_for_update(self._session, order.voucher_code)

        if usage is not None:
            usage.status = "RELEASED"
            usage.updated_at = datetime.now(timezone.utc)
            await commerce_repo.save_voucher_usage(self._session, usage)
        else:
            voucher_id = voucher.id if voucher else None
            if voucher_id:
                await commerce_repo.upsert_voucher_usage(
                    self._session,
                    id=uuid4(),
                    order_id=order.id,
                    voucher_id=voucher_id,
                    user_id=order.user_id,
                    discount_amount=order.voucher_discount_amount or Decimal("0"),
                    status="RELEASED",
                )

        if voucher is not None:
            voucher.used_count = max(0, int(voucher.used_count or 0) - 1)
            restored_discount = usage.discount_amount if usage else Decimal(order.voucher_discount_amount or 0)
            voucher.total_discount_used = max(Decimal("0"), Decimal(voucher.total_discount_used or 0) - restored_discount)
            commerce_repo.save_model(self._session, voucher)
        if order.voucher_claim_id:
            wallet_voucher = await commerce_repo.get_user_voucher_for_update(self._session, order.voucher_claim_id)
            if wallet_voucher is not None:
                now = datetime.now(timezone.utc)
                if wallet_voucher.expires_at and wallet_voucher.expires_at < now:
                    wallet_voucher.status = "EXPIRED"
                else:
                    wallet_voucher.status = "AVAILABLE"
                wallet_voucher.used_at = None
                wallet_voucher.order_id = None
                commerce_repo.save_model(self._session, wallet_voucher)

    def _invalid(
        self,
        code: str,
        error_code: str,
        message: str,
        metadata: dict | None = None,
    ) -> VoucherValidationResponse:
        return VoucherValidationResponse(
            code=code,
            valid=False,
            discount_amount=Decimal("0"),
            message=message,
            error_code=error_code,
            metadata=metadata or {},
        )

    def _wallet_response(self, wallet_voucher: UserVoucher, voucher: Voucher) -> UserVoucherResponse:
        status = wallet_voucher.status
        now = datetime.now(timezone.utc)
        if status == "AVAILABLE" and wallet_voucher.expires_at and wallet_voucher.expires_at < now:
            status = "EXPIRED"
        return UserVoucherResponse(
            id=str(wallet_voucher.id),
            voucher_id=str(wallet_voucher.voucher_id),
            user_id=str(wallet_voucher.user_id),
            code=voucher.code,
            status=status,
            claimed_at=wallet_voucher.claimed_at.isoformat() if wallet_voucher.claimed_at else None,
            expires_at=(wallet_voucher.expires_at or voucher.ends_at).isoformat() if (wallet_voucher.expires_at or voucher.ends_at) else None,
            used_at=wallet_voucher.used_at.isoformat() if wallet_voucher.used_at else None,
            order_id=str(wallet_voucher.order_id) if wallet_voucher.order_id else None,
            discount_type=voucher.discount_type,
            discount_amount=Decimal(voucher.discount_value),
            min_order_value=Decimal(voucher.min_order_value or 0),
            max_discount=Decimal(voucher.max_discount) if voucher.max_discount is not None else None,
            display_title=voucher.display_title,
            display_description=voucher.display_description,
            public_terms=voucher.public_terms,
            audience_type=voucher.audience_type,
            applicable_payment_methods=voucher.applicable_payment_methods if isinstance(voucher.applicable_payment_methods, list) else [],
            stackable=bool(voucher.stackable),
        )

    async def _expire_wallet_voucher(self, wallet_voucher: UserVoucher) -> None:
        wallet_voucher.status = "EXPIRED"
        commerce_repo.save_model(self._session, wallet_voucher)

    async def _get_active_voucher(self, code: str) -> Voucher | None:
        return await commerce_repo.get_active_voucher(self._session, code)

    async def _get_claimed_voucher(self, *, user_id: UUID, voucher_id: UUID) -> UserVoucher | None:
        return await commerce_repo.get_claimed_voucher(self._session, user_id=user_id, voucher_id=voucher_id)

    async def _user_order_count(self, user_id: UUID) -> int:
        return await commerce_repo.count_user_orders(self._session, user_id)

    async def _user_voucher_usage_count(self, user_id: UUID, code: str) -> int:
        return await commerce_repo.count_user_voucher_usage(self._session, user_id=user_id, code=code)

    async def _voucher_usage_count_by(self, column: str, value: str, code: str) -> int:
        if column not in {"voucher_device_id", "voucher_ip_address"}:
            return 0
        return await commerce_repo.count_voucher_usage_by_identity(
            self._session,
            column=column,
            value=value,
            code=code,
        )

    @staticmethod
    def _calculate_discount(*, voucher: Voucher, subtotal_amount: Decimal, context: VoucherValidationContext | None = None) -> Decimal:
        eligible_subtotal = context.eligible_subtotal if context else subtotal_amount
        if voucher.discount_type == "FIXED":
            discount = Decimal(voucher.discount_value)
        else:
            discount = eligible_subtotal * Decimal(voucher.discount_value) / Decimal("100")
            if voucher.max_discount is not None:
                discount = min(discount, Decimal(voucher.max_discount))
        return min(discount, eligible_subtotal)


async def expire_wallet_vouchers(session: AsyncSession, now: datetime) -> int:
    return await voucher_repo.expire_available_wallet_vouchers(session, now=now)
