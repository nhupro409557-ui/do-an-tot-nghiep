from .common import *

class VoucherService:
    # Rule pipeline keeps the voucher rules modular so future business rules can be added safely.
    _rules: tuple[VoucherRule, ...] = (
        VoucherActiveWindowRule(),
        VoucherWalletRule(),
        MinOrderRule(),
        ChannelPaymentRule(),
        UsageLimitRule(),
        BudgetRule(),
        AudienceRule(),
        FirstOrderRule(),
        AbandonedCartRule(),
        IdentityLimitRule(),
        TargetingRule(),
    )

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

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
    ) -> VoucherValidationResponse:
        voucher = await self._get_active_voucher(code)
        if voucher is None:
            return self._invalid(code.upper(), "VOUCHER_ERR_INVALID", "Voucher is invalid or inactive.")

        now = await commerce_repo.get_database_now(self._session)
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
        )
        for rule in self._rules:
            failure = await rule.check(self, context)
            if failure is not None:
                return failure

        discount = self._calculate_discount(voucher=voucher, subtotal_amount=subtotal_amount)
        if voucher.total_budget_cap is not None:
            remaining_budget = Decimal(voucher.total_budget_cap) - Decimal(voucher.total_discount_used or 0)
            if remaining_budget <= 0:
                return self._invalid(
                    voucher.code,
                    "VOUCHER_ERR_BUDGET",
                    "Voucher campaign budget has been reached.",
                    {"budget_cap": str(voucher.total_budget_cap), "used_budget": str(voucher.total_discount_used or 0)},
                )
            discount = min(discount, remaining_budget)
        return VoucherValidationResponse(
            code=voucher.code,
            valid=True,
            discount_amount=discount,
            message="Voucher applied successfully.",
            error_code=None,
            metadata={
                "stackable": bool(voucher.stackable),
                "wallet_claim_required": voucher.validity_days_after_claim > 0,
                "claimed_voucher_id": str(context.claimed_voucher.id) if context.claimed_voucher else None,
            },
        )

    async def claim_voucher(self, *, user_id: UUID, voucher_id: UUID) -> UserVoucherResponse:
        now = datetime.now(timezone.utc)
        voucher = await commerce_repo.get_voucher_by_id(self._session, voucher_id)
        if voucher is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voucher not found.")
        if voucher.status != "ACTIVE":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Voucher is not active.")

        existing = await commerce_repo.get_existing_user_voucher(self._session, user_id=user_id, voucher_id=voucher_id)
        if existing is not None:
            return self._wallet_response(existing, voucher)

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
        responses: list[UserVoucherResponse] = []
        now = datetime.now(timezone.utc)
        for wallet_voucher, voucher in await commerce_repo.list_user_vouchers_with_voucher(self._session, user_id):
            if wallet_voucher.expires_at and wallet_voucher.status == "AVAILABLE" and wallet_voucher.expires_at < now:
                await self._expire_wallet_voucher(wallet_voucher)
            responses.append(self._wallet_response(wallet_voucher, voucher))
        return responses

    async def mark_voucher_used(
        self,
        *,
        voucher: Voucher,
        order_id: UUID,
        discount_amount: Decimal,
        user_id: UUID | None,
    ) -> UserVoucher | None:
        claimed_voucher = None
        if voucher.validity_days_after_claim > 0 and user_id:
            claimed_voucher = await commerce_repo.get_claimed_voucher_for_update(
                self._session,
                user_id=user_id,
                voucher_id=voucher.id,
            )
        voucher.used_count += 1
        voucher.total_discount_used = Decimal(voucher.total_discount_used or 0) + discount_amount
        commerce_repo.save_model(self._session, voucher)
        if claimed_voucher is not None:
            claimed_voucher.status = "USED"
            claimed_voucher.used_at = datetime.now(timezone.utc)
            claimed_voucher.order_id = order_id
            commerce_repo.save_model(self._session, claimed_voucher)
        return claimed_voucher

    async def rollback_voucher_usage(self, *, order: Order) -> None:
        if not order.voucher_code:
            return
        voucher = await commerce_repo.get_voucher_by_order_code_for_update(self._session, order.voucher_code)
        if voucher is not None:
            voucher.used_count = max(0, int(voucher.used_count or 0) - 1)
            restored_discount = min(
                Decimal(voucher.total_discount_used or 0),
                Decimal(order.discount_amount or 0),
            )
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
        return UserVoucherResponse(
            id=str(wallet_voucher.id),
            voucher_id=str(wallet_voucher.voucher_id),
            user_id=str(wallet_voucher.user_id),
            code=voucher.code,
            status=wallet_voucher.status,
            claimed_at=wallet_voucher.claimed_at.isoformat() if wallet_voucher.claimed_at else None,
            expires_at=wallet_voucher.expires_at.isoformat() if wallet_voucher.expires_at else None,
            used_at=wallet_voucher.used_at.isoformat() if wallet_voucher.used_at else None,
            order_id=str(wallet_voucher.order_id) if wallet_voucher.order_id else None,
            discount_type=voucher.discount_type,
            discount_amount=Decimal(voucher.discount_value),
            min_order_value=Decimal(voucher.min_order_value or 0),
            max_discount=Decimal(voucher.max_discount) if voucher.max_discount is not None else None,
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
    def _calculate_discount(*, voucher: Voucher, subtotal_amount: Decimal) -> Decimal:
        if voucher.discount_type == "FIXED":
            discount = Decimal(voucher.discount_value)
        else:
            discount = subtotal_amount * Decimal(voucher.discount_value) / Decimal("100")
            if voucher.max_discount is not None:
                discount = min(discount, Decimal(voucher.max_discount))
        return min(discount, subtotal_amount)
