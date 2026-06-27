from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.message import EmailMessage
import json
import secrets
import smtplib
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.commerce.integrations import RefundGateway, ShippingGateway, normalize_mock_carrier
from app.application.commerce.integrations import MoMoSandboxGateway, SandboxShippingPricingService, SePayPaymentGateway, ZaloPaySandboxGateway
from app.application.commerce.schemas import (
    AdminUpdateOrderRequest,
    CarrierShipmentResponse,
    CreateOrderRequest,
    CreateOrderResponse,
    PaymentStatusResponse,
    RevenueReportResponse,
    ShippingQuoteResponse,
    UserVoucherResponse,
    VoucherValidationResponse,
)
from app.config import settings
from app.infrastructure.database.repositories import commerce_repo, order_repo


ORDER_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"PAID", "PROCESSING", "CANCELLED", "PAYMENT_FAILED"},
    "CONFIRMED": {"PROCESSING", "CANCELLED"},
    "PAID": {"PROCESSING", "CANCELLED", "REFUNDED", "PAYMENT_FAILED"},
    "PROCESSING": {"SHIPPED", "CANCELLED", "PAYMENT_FAILED"},
    "SHIPPED": {"COMPLETED", "REFUNDED", "RETURNING"},
    "COMPLETED": {"RETURNING"},
    "CANCELLED": set(),
    "REFUNDED": set(),
    "PAYMENT_FAILED": {"PAID"},
    "RETURNING": {"RETURNED", "REFUNDED"},
    "RETURNED": {"REFUNDED"},
}

ORDER_STATUS_EMAIL_LABELS: dict[str, str] = {
    "PENDING": "Cho xu ly",
    "CONFIRMED": "Da xac nhan",
    "PAID": "Da thanh toan",
    "PROCESSING": "Dang dong goi",
    "SHIPPED": "Dang giao",
    "COMPLETED": "Da giao",
    "CANCELLED": "Da huy",
    "REFUNDED": "Da hoan tien",
    "PAYMENT_FAILED": "Thanh toan that bai",
    "RETURNING": "Dang hoan hang",
    "RETURNED": "Da nhan hang hoan",
}


def generate_order_code() -> str:
    return f"EMV{secrets.randbelow(10_000_000_000):010d}"


from app.domain.users.entities import LoyaltyTransactionType
from app.infrastructure.database.models import (
    LoyaltyTransaction,
    Order,
    OrderHistoryLog,
    OrderItem,
    PaymentTransaction,
    User,
    UserVoucher,
    Voucher,
)


def calculate_tier(points: int) -> str:
    if points >= 15000:
        return "DIAMOND"
    if points >= 8000:
        return "GOLD"
    if points >= 3000:
        return "SILVER"
    return "MEMBER"


@dataclass
class VoucherValidationContext:
    voucher: Voucher
    now: datetime
    subtotal_amount: Decimal
    user_id: UUID | None = None
    user_tier: str | None = None
    abandoned_cart_recovery: bool = False
    device_id: str | None = None
    ip_address: str | None = None
    payment_method: str | None = None
    channel: str | None = None
    product_ids: set[str] = field(default_factory=set)
    category_ids: set[str] = field(default_factory=set)
    brand_ids: set[str] = field(default_factory=set)
    claimed_voucher: UserVoucher | None = None


class VoucherRule:
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        return None


class VoucherActiveWindowRule(VoucherRule):
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        voucher = context.voucher
        if voucher.starts_at and voucher.starts_at > context.now:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_NOT_STARTED",
                "Voucher is not active yet.",
                {"starts_at": voucher.starts_at.isoformat()},
            )
        if voucher.ends_at and voucher.ends_at < context.now:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_EXPIRED",
                "Voucher has expired.",
                {"ends_at": voucher.ends_at.isoformat()},
            )
        return None


class VoucherWalletRule(VoucherRule):
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        voucher = context.voucher
        if voucher.validity_days_after_claim <= 0:
            return None
        if not context.user_id:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_SIGN_IN_REQUIRED",
                "Please sign in and claim this voucher before applying it.",
            )
        claimed = await service._get_claimed_voucher(user_id=context.user_id, voucher_id=voucher.id)
        if claimed is None:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_CLAIM_REQUIRED",
                "This voucher must be claimed to your wallet before use.",
                {"claim_window_days": voucher.validity_days_after_claim},
            )
        if claimed.expires_at and claimed.expires_at < context.now:
            await service._expire_wallet_voucher(claimed)
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_WALLET_EXPIRED",
                "Your claimed voucher has expired.",
                {"expires_at": claimed.expires_at.isoformat()},
            )
        if claimed.status not in {"AVAILABLE", "RESERVED"}:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_WALLET_UNAVAILABLE",
                "This voucher is no longer available in your wallet.",
                {"wallet_status": claimed.status},
            )
        context.claimed_voucher = claimed
        return None


class MinOrderRule(VoucherRule):
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        minimum = Decimal(context.voucher.min_order_value or 0)
        if context.subtotal_amount >= minimum:
            return None
        shortfall = max(Decimal("0"), minimum - context.subtotal_amount)
        return service._invalid(
            context.voucher.code,
            "VOUCHER_ERR_MIN_ORDER",
            f"Order amount must reach at least {minimum:,.0f} to use this voucher.",
            {
                "current_subtotal": str(context.subtotal_amount),
                "minimum_order_value": str(minimum),
                "shortfall_amount": str(shortfall),
            },
        )


class ChannelPaymentRule(VoucherRule):
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        voucher = context.voucher
        channels = voucher.applicable_channels if isinstance(voucher.applicable_channels, list) else []
        payment_methods = voucher.applicable_payment_methods if isinstance(voucher.applicable_payment_methods, list) else []
        allowed_channels = {str(channel).upper() for channel in channels if channel}
        allowed_payment_methods = {str(method).upper() for method in payment_methods if method}

        if allowed_channels and context.channel and context.channel.upper() not in allowed_channels:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_CHANNEL",
                "Voucher is not available on this channel.",
                {"allowed_channels": sorted(allowed_channels), "current_channel": context.channel},
            )
        if allowed_payment_methods and context.payment_method and context.payment_method.upper() not in allowed_payment_methods:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_PAYMENT_METHOD",
                "Voucher is not available for this payment method.",
                {"allowed_payment_methods": sorted(allowed_payment_methods), "current_payment_method": context.payment_method},
            )
        return None


class UsageLimitRule(VoucherRule):
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        voucher = context.voucher
        if voucher.usage_limit > 0 and voucher.used_count >= voucher.usage_limit:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_USAGE_LIMIT",
                "Voucher usage limit has been reached.",
                {"usage_limit": voucher.usage_limit, "used_count": voucher.used_count},
            )
        return None


class BudgetRule(VoucherRule):
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        voucher = context.voucher
        if voucher.total_budget_cap is None:
            return None
        budget_cap = Decimal(voucher.total_budget_cap)
        used_budget = Decimal(voucher.total_discount_used or 0)
        if used_budget >= budget_cap:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_BUDGET",
                "Voucher campaign budget has been reached.",
                {"budget_cap": str(budget_cap), "used_budget": str(used_budget)},
            )
        return None


class AudienceRule(VoucherRule):
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        voucher = context.voucher
        if voucher.assigned_user_id and voucher.assigned_user_id != context.user_id:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_ASSIGNED_USER",
                "Voucher is reserved for another customer.",
            )
        if voucher.audience_type == "SPECIFIC_USER" and not voucher.assigned_user_id:
            if not context.user_id:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_ASSIGNED_USER_SIGN_IN",
                    "Please sign in to use this assigned voucher.",
                )
            if not await commerce_repo.has_user_voucher_assignment(
                service._session,
                user_id=context.user_id,
                voucher_id=voucher.id,
            ):
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_ASSIGNED_USER",
                    "Voucher is reserved for another customer.",
                )
        if voucher.eligible_user_registered_after and context.user_id:
            registered_at = await commerce_repo.get_user_created_at(service._session, context.user_id)
            if registered_at and registered_at < voucher.eligible_user_registered_after:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_NEW_USER_ONLY",
                    "Voucher is only for newer accounts.",
                    {"eligible_user_registered_after": voucher.eligible_user_registered_after.isoformat()},
                )
        eligible_tiers = voucher.eligible_tiers if isinstance(voucher.eligible_tiers, list) else []
        if eligible_tiers and (context.user_tier or "").upper() not in {str(tier).upper() for tier in eligible_tiers}:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_TIER",
                "Voucher is not available for your membership tier.",
                {"eligible_tiers": eligible_tiers, "current_tier": context.user_tier},
            )
        return None


class FirstOrderRule(VoucherRule):
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        if not context.voucher.first_order_only:
            return None
        if not context.user_id:
            return service._invalid(
                context.voucher.code,
                "VOUCHER_ERR_FIRST_ORDER_SIGN_IN",
                "Please sign in to use this first-order voucher.",
            )
        if await service._user_order_count(context.user_id) > 0:
            return service._invalid(
                context.voucher.code,
                "VOUCHER_ERR_FIRST_ORDER_ONLY",
                "Voucher is only for the first order.",
            )
        return None


class AbandonedCartRule(VoucherRule):
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        if context.voucher.abandoned_cart_only and not context.abandoned_cart_recovery:
            return service._invalid(
                context.voucher.code,
                "VOUCHER_ERR_ABANDONED_CART",
                "Voucher is only available from an abandoned cart recovery offer.",
            )
        return None


class IdentityLimitRule(VoucherRule):
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        voucher = context.voucher
        if voucher.per_user_limit > 0 and context.user_id:
            usage = await service._user_voucher_usage_count(context.user_id, voucher.code)
            if usage >= voucher.per_user_limit:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_USER_LIMIT",
                    "Voucher per-customer limit has been reached.",
                    {"per_user_limit": voucher.per_user_limit, "used_count": usage},
                )
        if voucher.per_device_limit > 0 and context.device_id:
            usage = await service._voucher_usage_count_by("voucher_device_id", context.device_id, voucher.code)
            if usage >= voucher.per_device_limit:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_DEVICE_LIMIT",
                    "Voucher device limit has been reached.",
                    {"per_device_limit": voucher.per_device_limit, "used_count": usage},
                )
        if voucher.per_ip_limit > 0 and context.ip_address:
            usage = await service._voucher_usage_count_by("voucher_ip_address", context.ip_address, voucher.code)
            if usage >= voucher.per_ip_limit:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_IP_LIMIT",
                    "Voucher IP limit has been reached.",
                    {"per_ip_limit": voucher.per_ip_limit, "used_count": usage},
                )
        return None


class TargetingRule(VoucherRule):
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        voucher = context.voucher
        include_products = set(voucher.include_product_ids if isinstance(voucher.include_product_ids, list) else [])
        exclude_products = set(voucher.exclude_product_ids if isinstance(voucher.exclude_product_ids, list) else [])
        include_categories = set(voucher.include_category_ids if isinstance(voucher.include_category_ids, list) else [])
        exclude_categories = set(voucher.exclude_category_ids if isinstance(voucher.exclude_category_ids, list) else [])
        include_brands = set(voucher.include_brand_ids if isinstance(voucher.include_brand_ids, list) else [])
        exclude_brands = set(voucher.exclude_brand_ids if isinstance(voucher.exclude_brand_ids, list) else [])
        if include_products and not context.product_ids.intersection(include_products):
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_PRODUCT_SCOPE",
                "Voucher does not apply to products in this order.",
                {"required_product_ids": sorted(include_products)},
            )
        if exclude_products:
            blocked = sorted(context.product_ids.intersection(exclude_products))
            if blocked:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_PRODUCT_EXCLUDED",
                    "Voucher excludes one or more products in this order.",
                    {"blocked_product_ids": blocked},
                )
        if include_categories and not context.category_ids.intersection(include_categories):
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_CATEGORY_SCOPE",
                "Voucher does not apply to categories in this order.",
                {"required_category_ids": sorted(include_categories)},
            )
        if exclude_categories:
            blocked = sorted(context.category_ids.intersection(exclude_categories))
            if blocked:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_CATEGORY_EXCLUDED",
                    "Voucher excludes one or more categories in this order.",
                    {"blocked_category_ids": blocked},
                )
        if include_brands and not context.brand_ids.intersection(include_brands):
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_BRAND_SCOPE",
                "Voucher does not apply to brands in this order.",
                {"required_brand_ids": sorted(include_brands)},
            )
        if exclude_brands:
            blocked = sorted(context.brand_ids.intersection(exclude_brands))
            if blocked:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_BRAND_EXCLUDED",
                    "Voucher excludes one or more brands in this order.",
                    {"blocked_brand_ids": blocked},
                )
        return None


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

            for item in request.items:
                commerce_repo.save_model(
                    self._session,
                    OrderItem(
                        id=uuid4(),
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
                # Trừ kho thực tế bằng FIFO
                complete_use_case = CompleteOrderUseCase(session=self._session)
                await complete_use_case._ship_order_items(order)
                
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


class PaymentUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session
        self._momo_gateway = MoMoSandboxGateway()
        self._sepay_gateway = SePayPaymentGateway()
        self._zalopay_gateway = ZaloPaySandboxGateway()

    async def _mark_order_payment_failed_if_pending(self, order_id: UUID, *, internal_note: str, changed_by: str) -> None:
        order = await self._session.get(Order, order_id)
        if order is None or order.status != "PENDING":
            await self._session.rollback()
            return
        await self._session.rollback()
        await CompleteOrderUseCase(session=self._session).execute(
            order_id=order_id,
            status_value="PAYMENT_FAILED",
            internal_note=internal_note,
            changed_by=changed_by,
        )

    async def get_status(self, payment_id: UUID) -> PaymentStatusResponse:
        payment = await commerce_repo.get_payment_transaction(self._session, payment_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch thanh toán.")
        order = await self._session.get(Order, payment.order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")

        # Truy vấn trực tiếp trạng thái từ MoMo nếu giao dịch đang chờ (PENDING)
        if payment.status == "PENDING" and payment.provider == "MOMO":
            try:
                momo_result = await self._momo_gateway.query_payment(
                    order_code=payment.transaction_ref,
                    request_id=str(payment.id),
                )
                # resultCode = 0 nghĩa là thanh toán thành công
                if momo_result.get("resultCode") == 0:
                    payment.status = "PAID"
                    payment.paid_at = datetime.now(timezone.utc)
                    payment.raw_response = {**(payment.raw_response or {}), "query_api": momo_result}
                    commerce_repo.save_model(self._session, payment)
                    await self._session.commit()
                    # Cập nhật đơn hàng thành PAID
                    await CompleteOrderUseCase(session=self._session).execute(
                        order_id=payment.order_id,
                        status_value="PAID",
                        internal_note="Xác nhận thanh toán tự động qua truy vấn API MoMo.",
                        changed_by="momo-query-api",
                    )
                    # Tải lại order và payment sau khi commit
                    payment = await commerce_repo.get_payment_transaction(self._session, payment_id)
                    order = await self._session.get(Order, payment.order_id)
            except Exception as e:
                import logging
                logger = logging.getLogger("uvicorn.error")
                logger.error("Lỗi khi đối soát tự động MoMo: %s", e)

        now = datetime.now(timezone.utc)
        if payment.status == "PENDING" and payment.expires_at and payment.expires_at <= now:
            payment.status = "EXPIRED"
            payment.failed_at = now
            payment.raw_response = {
                **(payment.raw_response or {}),
                "failure_message": "Phiên thanh toán đã hết hạn.",
            }
            commerce_repo.save_model(self._session, payment)
            await self._session.commit()
            if order.status == "PENDING":
                await self._mark_order_payment_failed_if_pending(
                    order_id=payment.order_id,
                    internal_note="Phiên thanh toán đã hết hạn.",
                    changed_by="payment-expirer",
                )
                order = await self._session.get(Order, payment.order_id)
        raw_response = payment.raw_response or {}
        return PaymentStatusResponse(
            id=payment.id,
            order_id=payment.order_id,
            order_code=order.order_code,
            order_status=order.status,
            provider=payment.provider,
            amount=Decimal(payment.amount),
            status=payment.status,
            attempt_number=payment.attempt_number,
            checkout_url=payment.checkout_url,
            checkout_method=raw_response.get("checkout_method"),
            checkout_fields=raw_response.get("checkout_fields") if isinstance(raw_response.get("checkout_fields"), dict) else {},
            expires_at=payment.expires_at.isoformat() if payment.expires_at else None,
            paid_at=payment.paid_at.isoformat() if payment.paid_at else None,
            failure_message=raw_response.get("failure_message"),
        )

    async def cancel(self, payment_id: UUID) -> PaymentStatusResponse:
        payment = await commerce_repo.get_payment_transaction(self._session, payment_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch thanh toán.")
        order = await self._session.get(Order, payment.order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
        if payment.status in {"PAID", "REFUNDED"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Giao dịch đã hoàn tất, không thể hủy.")
        now = datetime.now(timezone.utc)
        if payment.status == "PENDING":
            payment.status = "FAILED"
            payment.failed_at = now
            payment.raw_response = {
                **(payment.raw_response or {}),
                "failure_message": "Khách hàng đã hủy phiên thanh toán.",
            }
            commerce_repo.save_model(self._session, payment)
            await self._session.commit()
            if order.status == "PENDING":
                await self._mark_order_payment_failed_if_pending(
                    order_id=payment.order_id,
                    internal_note="Khách hàng đã hủy phiên thanh toán.",
                    changed_by="customer-payment-cancel",
                )
        return await self.get_status(payment.id)

    async def retry(self, payment_id: UUID) -> PaymentStatusResponse:
        previous = await commerce_repo.get_payment_transaction(self._session, payment_id)
        if previous is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch thanh toán.")
        order = await commerce_repo.get_order_for_update(self._session, previous.order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
        if order.payment_status == "PAID":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Đơn hàng đã được thanh toán.")
        if order.status != "PENDING":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Đơn hàng không còn chờ thanh toán.")
        latest = await commerce_repo.get_latest_payment_transaction(self._session, order.id)
        now = datetime.now(timezone.utc)
        if latest and latest.status == "PENDING" and (not latest.expires_at or latest.expires_at > now):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phiên thanh toán hiện tại vẫn còn hiệu lực.")
        next_attempt = (latest.attempt_number if latest else 0) + 1
        payment_id_new = uuid4()
        if previous.provider == "MOMO":
            provider_order_id = f"{order.order_code}-{next_attempt}"
            payment_init = await self._momo_gateway.create_payment(
                order_code=provider_order_id,
                amount=Decimal(order.total_amount),
                order_info=f"Thanh toán lại đơn hàng {order.order_code}",
                extra_data={"orderCode": order.order_code, "attempt": next_attempt},
                request_id=str(payment_id_new),
            )
            timeout_minutes = settings.momo_payment_timeout_minutes
        elif previous.provider == "ZALOPAY":
            vietnam_date = datetime.now(timezone(timedelta(hours=7))).strftime("%y%m%d")
            provider_order_id = f"{vietnam_date}_{order.order_code[-10:]}{next_attempt:02d}"
            payment_init = await self._zalopay_gateway.create_payment(
                app_trans_id=provider_order_id,
                amount=Decimal(order.total_amount),
                app_user=str(order.user_id or "electromart-sandbox"),
                description=f"ElectroMart Sandbox - Thanh toán lại đơn hàng {order.order_code}",
                callback_url=settings.zalopay_callback_url,
                redirect_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_id_new}",
            )
            timeout_minutes = settings.zalopay_payment_timeout_minutes
        elif previous.provider == "SEPAY":
            provider_order_id = f"{order.order_code}-{next_attempt}"
            payment_init = self._sepay_gateway.create_checkout(
                order_invoice_number=provider_order_id,
                order_amount=Decimal(order.total_amount),
                order_description=f"Thanh toán lại đơn hàng {order.order_code}",
                success_url=f"{settings.frontend_url.rstrip('/')}/orders/{order.id}?payment=success",
                error_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_id_new}?payment=error",
                cancel_url=f"{settings.frontend_url.rstrip('/')}/payment/{payment_id_new}?payment=cancel",
                customer_id=str(order.user_id) if order.user_id else None,
            )
            timeout_minutes = settings.sepay_payment_timeout_minutes
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cổng thanh toán không hỗ trợ thử lại.")
        expires_at = now + timedelta(minutes=timeout_minutes)
        payment = PaymentTransaction(
            id=payment_id_new,
            order_id=order.id,
            provider=previous.provider,
            amount=order.total_amount,
            status="PENDING",
            transaction_ref=provider_order_id,
            checkout_url=payment_init.checkout_url,
            attempt_number=next_attempt,
            expires_at=expires_at,
            raw_response=payment_init.raw_response or {},
        )
        commerce_repo.save_model(self._session, payment)
        await self._session.commit()
        return await self.get_status(payment.id)

    async def process_sepay_ipn(self, payload: dict, *, secret_key: str | None) -> dict:
        import re
        
        # 1. Trích xuất mã đơn hàng bằng Regex từ các trường payload (hỗ trợ cả EMV và EC)
        order_code = ""
        for field_name in ["code", "transactionContent", "transaction_content", "content", "description", "body", "order_invoice_number", "invoice_number", "order_id", "orderCode"]:
            field_val = payload.get(field_name)
            if field_val and isinstance(field_val, str):
                match = re.search(r"EMV[0-9]{6,12}|EC[0-9A-Z]{10}", field_val.upper())
                if match:
                    order_code = match.group(0)
                    break
        
        # 2. Lấy invoice_number (SePay Checkout Link) nếu có
        invoice_number = str(
            payload.get("order_invoice_number")
            or payload.get("invoice_number")
            or payload.get("order_id")
            or payload.get("orderCode")
            or ""
        )
        
        # Nếu không trích xuất được cả order_code lẫn invoice_number, ném lỗi
        if not order_code and not invoice_number:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu mã đơn SePay hoặc nội dung chuyển tiền không chứa mã đơn hàng.")

        signature_valid = self._sepay_gateway.verify_ipn_secret(secret_key)
        
        # Tạo event_key duy nhất dựa trên ID giao dịch để tránh xử lý trùng lặp
        transaction_id = str(
            payload.get("id")
            or payload.get("transaction_id")
            or payload.get("sepay_transaction_id")
            or payload.get("reference_id")
            or ""
        )
        event_key = ":".join(
            [
                invoice_number or order_code,
                transaction_id,
                str(payload.get("event_type") or payload.get("order_status") or payload.get("status") or ""),
            ]
        )
        
        # Thử tìm PaymentTransaction bằng invoice_number trước (SePay Checkout Link)
        payment = None
        if invoice_number:
            payment = await commerce_repo.get_payment_transaction_by_reference_for_update(
                self._session,
                provider="SEPAY",
                transaction_ref=invoice_number,
            )

        # Nếu không tìm thấy, thử tìm qua mã đơn hàng trích xuất bằng Regex (Chuyển khoản Ngân hàng Trực tiếp)
        if payment is None and order_code:
            from app.infrastructure.database.repositories import order_repo
            order_id = await order_repo.get_order_id_by_code(self._session, order_code)
            if order_id:
                # Lấy giao dịch thanh toán gần nhất của đơn hàng
                payment = await commerce_repo.get_latest_payment_transaction(self._session, order_id)
                
                # Nếu chưa tồn tại giao dịch thanh toán (khách chuyển khoản trực tiếp bằng ngân hàng)
                if payment is None:
                    order = await self._session.get(Order, order_id)
                    if order:
                        from datetime import timedelta
                        payment = PaymentTransaction(
                            id=uuid4(),
                            order_id=order.id,
                            provider="SEPAY",
                            amount=order.total_amount,
                            status="PENDING",
                            transaction_ref=order_code,
                            attempt_number=1,
                            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
                            raw_response={"note": "Tự động tạo từ Webhook chuyển khoản trực tiếp SePay"},
                        )
                        commerce_repo.save_model(self._session, payment)
                        await self._session.flush()

        event_id = uuid4()
        inserted = await commerce_repo.create_webhook_event(
            self._session,
            event_id=event_id,
            provider="SEPAY",
            event_key=event_key,
            order_id=payment.order_id if payment else None,
            payment_transaction_id=payment.id if payment else None,
            signature_valid=signature_valid,
            payload=payload,
        )
        if not inserted:
            await self._session.rollback()
            return {"success": True, "duplicate": True}
        if not signature_valid:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Secret key IPN SePay không hợp lệ.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Secret key IPN không hợp lệ.")
        if payment is None:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Không tìm thấy giao dịch SePay.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch SePay.")

        # Lấy số tiền thực nhận (hỗ trợ các trường của chuyển khoản ngân hàng SePay như transferAmount, amountIn)
        paid_amount = Decimal(
            str(
                payload.get("transferAmount")
                or payload.get("amountIn")
                or payload.get("order_amount")
                or payload.get("amount")
                or payload.get("transaction_amount")
                or payload.get("total_amount")
                or 0
            )
        )
        if paid_amount != Decimal(payment.amount):
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Số tiền IPN SePay không khớp giao dịch.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số tiền thanh toán không khớp.")
        if payment.status in {"PAID", "REFUNDED"}:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="IGNORED",
            )
            await self._session.commit()
            return {"success": True, "duplicate": True}

        event_type = str(payload.get("event_type") or payload.get("order_status") or payload.get("status") or "").upper()
        transfer_type = str(payload.get("transferType") or "").lower()
        amount_in = Decimal(str(payload.get("amountIn") or 0))
        if not event_type and (transfer_type == "in" or amount_in > 0):
            event_type = "PAID"

        now = datetime.now(timezone.utc)
        payment.raw_response = {**(payment.raw_response or {}), "ipn": payload}
        if event_type in {"ORDER_PAID", "PAID", "SUCCESS", "SUCCEEDED"}:
            payment.status = "PAID"
            payment.paid_at = now
            commerce_repo.save_model(self._session, payment)
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="PROCESSED",
            )
            await self._session.commit()
            await CompleteOrderUseCase(session=self._session).execute(
                order_id=payment.order_id,
                status_value="PAID",
                internal_note="SePay IPN xác nhận thanh toán thành công.",
                changed_by="sepay-ipn",
            )
        else:
            payment.status = "FAILED"
            payment.failed_at = now
            payment.raw_response = {
                **payment.raw_response,
                "failure_message": str(payload.get("message") or f"SePay event={event_type}"),
            }
            commerce_repo.save_model(self._session, payment)
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="PROCESSED",
            )
            await self._session.commit()
            await self._mark_order_payment_failed_if_pending(
                order_id=payment.order_id,
                internal_note="SePay IPN báo thanh toán không thành công.",
                changed_by="sepay-ipn",
            )
        return {"success": True, "duplicate": False}

    async def process_momo_ipn(self, payload: dict) -> dict:
        provider_order_id = str(payload.get("orderId") or "")
        if not provider_order_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu orderId.")
        signature_valid = self._momo_gateway.verify_ipn_signature(payload)
        event_key = ":".join(
            [
                str(payload.get("partnerCode") or ""),
                provider_order_id,
                str(payload.get("requestId") or ""),
                str(payload.get("transId") or ""),
                str(payload.get("resultCode") or ""),
            ]
        )
        payment = await commerce_repo.get_payment_transaction_by_reference_for_update(
            self._session,
            provider="MOMO",
            transaction_ref=provider_order_id,
        )
        order_id = payment.order_id if payment else None
        event_id = uuid4()
        inserted = await commerce_repo.create_webhook_event(
            self._session,
            event_id=event_id,
            provider="MOMO",
            event_key=event_key,
            order_id=order_id,
            payment_transaction_id=payment.id if payment else None,
            signature_valid=signature_valid,
            payload=payload,
        )
        if not inserted:
            await self._session.rollback()
            return {"ok": True, "duplicate": True}
        if not signature_valid:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Chữ ký IPN MoMo không hợp lệ.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chữ ký IPN không hợp lệ.")
        if order_id is None or payment is None:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Không tìm thấy đơn hàng hoặc giao dịch.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch.")
        if Decimal(str(payload.get("amount") or 0)) != Decimal(payment.amount):
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Số tiền IPN không khớp giao dịch.",
            )
            await self._session.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số tiền thanh toán không khớp.")
        if payment.status in {"PAID", "REFUNDED"}:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="IGNORED",
            )
            await self._session.commit()
            return {"ok": True, "duplicate": True}

        result_code = int(payload.get("resultCode") or -1)
        now = datetime.now(timezone.utc)
        payment.raw_response = {**(payment.raw_response or {}), "ipn": payload}
        if result_code == 0:
            payment.status = "PAID"
            payment.paid_at = now
            commerce_repo.save_model(self._session, payment)
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="PROCESSED",
            )
            await self._session.commit()
            await CompleteOrderUseCase(session=self._session).execute(
                order_id=order_id,
                status_value="PAID",
                internal_note="MoMo Sandbox IPN xác nhận thanh toán thành công.",
                changed_by="momo-sandbox-ipn",
            )
        else:
            payment.status = "FAILED"
            payment.failed_at = now
            payment.raw_response = {
                **payment.raw_response,
                "failure_message": str(payload.get("message") or f"MoMo resultCode={result_code}"),
            }
            commerce_repo.save_model(self._session, payment)
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="PROCESSED",
            )
            await self._session.commit()
            await self._mark_order_payment_failed_if_pending(
                order_id=order_id,
                internal_note="MoMo Sandbox IPN báo thanh toán không thành công.",
                changed_by="momo-sandbox-ipn",
            )
        return {"ok": True, "duplicate": False}

    async def process_zalopay_callback(self, payload: dict) -> dict:
        callback_data = str(payload.get("data") or "")
        callback_mac = str(payload.get("mac") or "")
        if not self._zalopay_gateway.verify_callback(callback_data, callback_mac):
            return {"return_code": -1, "return_message": "mac not equal"}
        try:
            data = json.loads(callback_data)
        except ValueError:
            return {"return_code": 0, "return_message": "callback data invalid"}
        app_trans_id = str(data.get("app_trans_id") or "")
        payment = await commerce_repo.get_payment_transaction_by_reference_for_update(
            self._session,
            provider="ZALOPAY",
            transaction_ref=app_trans_id,
        )
        event_id = uuid4()
        event_key = f"{app_trans_id}:{data.get('zp_trans_id', '')}"
        inserted = await commerce_repo.create_webhook_event(
            self._session,
            event_id=event_id,
            provider="ZALOPAY",
            event_key=event_key,
            order_id=payment.order_id if payment else None,
            payment_transaction_id=payment.id if payment else None,
            signature_valid=True,
            payload=payload,
        )
        if not inserted:
            await self._session.rollback()
            return {"return_code": 2, "return_message": "duplicate"}
        if payment is None:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Không tìm thấy giao dịch ZaloPay.",
            )
            await self._session.commit()
            return {"return_code": 0, "return_message": "payment not found"}
        if Decimal(str(data.get("amount") or 0)) != Decimal(payment.amount):
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="FAILED",
                error_message="Số tiền callback không khớp giao dịch.",
            )
            await self._session.commit()
            return {"return_code": -1, "return_message": "amount not equal"}
        if payment.status in {"PAID", "REFUNDED"}:
            await commerce_repo.finish_webhook_event(
                self._session,
                event_id=event_id,
                processing_status="IGNORED",
            )
            await self._session.commit()
            return {"return_code": 2, "return_message": "duplicate"}

        payment.status = "PAID"
        payment.paid_at = datetime.now(timezone.utc)
        payment.transaction_ref = app_trans_id
        payment.raw_response = {
            **(payment.raw_response or {}),
            "callback": data,
            "zp_trans_id": data.get("zp_trans_id"),
        }
        commerce_repo.save_model(self._session, payment)
        await commerce_repo.finish_webhook_event(
            self._session,
            event_id=event_id,
            processing_status="PROCESSED",
        )
        await self._session.commit()
        await CompleteOrderUseCase(session=self._session).execute(
            order_id=payment.order_id,
            status_value="PAID",
            internal_note="ZaloPay Sandbox callback xác nhận thanh toán thành công.",
            changed_by="zalopay-sandbox-callback",
        )
        return {"return_code": 1, "return_message": "success"}


class CompleteOrderUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session
        self._refund_gateway = RefundGateway()
        self._shipping_gateway = ShippingGateway()

    # Keep order state changes centralized so stock, payment, and loyalty side effects stay consistent.
    async def execute(
        self,
        *,
        order_id: UUID,
        status_value: str | None = None,
        assigned_staff_name: str | None = None,
        internal_note: str | None = None,
        cancellation_reason: str | None = None,
        shipping_provider: str | None = None,
        tracking_code: str | None = None,
        refund_payment: bool = False,
        changed_by: str | None = None,
        issue_allocations: list | None = None,
    ) -> None:
        async with self._session.begin():
            order = await commerce_repo.get_order_for_update(self._session, order_id)
            if order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

            previous_status = order.status
            now = datetime.now(timezone.utc)

            if assigned_staff_name is not None:
                order.assigned_staff_name = assigned_staff_name.strip() or None
            if internal_note is not None:
                order.internal_note = internal_note.strip() or None
            if shipping_provider is not None:
                order.shipping_provider = shipping_provider.strip() or None
            if tracking_code is not None:
                order.tracking_code = tracking_code.strip() or None

            if status_value is not None and status_value != previous_status:
                allowed_transitions = ORDER_STATUS_TRANSITIONS.get(previous_status, set())
                if status_value not in allowed_transitions:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Cannot move order from {previous_status} to {status_value}.",
                    )

                if status_value == "CANCELLED" and not (cancellation_reason or order.cancellation_reason):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cancellation reason is required when cancelling an order.",
                    )

                order.status = status_value
                if status_value in {"PAID", "COMPLETED"}:
                    order.payment_status = "PAID"
                if status_value in {"PROCESSING", "PAID"}:
                    from app.application.services.inventory_service import create_outbound_document_from_order
                    await create_outbound_document_from_order(self._session, order.id)
                if status_value == "SHIPPED":
                    # Check if there is an outbound document linked to this order
                    outbound_res = await self._session.execute(
                        text("SELECT id, status, document_no FROM inventory_documents WHERE order_id = :order_id AND document_type = 'OUTBOUND'"),
                        {"order_id": order.id}
                    )
                    outbound_row = outbound_res.mappings().first()
                    if outbound_row:
                        if outbound_row["status"] == "COMPLETED":
                            # Physical inventory is already posted, skip shipping items logic.
                            # But we MUST close active reservations as CONSUMED!
                            await commerce_repo.close_active_order_reservations(
                                self._session,
                                order_id=order.id,
                                status="CONSUMED",
                            )
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Đơn hàng đang có phiếu xuất kho chưa hoàn tất ({outbound_row['document_no']}). Vui lòng hoàn tất phiếu xuất kho để giao hàng."
                            )
                    else:
                        # Fallback to default FIFO shipping
                        await self._ship_order_items(order, issue_allocations=issue_allocations or [])

                    shipment = await self._shipping_gateway.register_shipment(
                        provider=order.shipping_provider,
                        order_code=order.order_code,
                        recipient_name=order.recipient_name,
                        recipient_phone=order.recipient_phone,
                        shipping_address=order.shipping_address,
                    )
                    if shipment.success:
                        order.shipping_provider = shipment.provider or order.shipping_provider
                        order.tracking_code = order.tracking_code or shipment.tracking_code
                    order.shipped_at = now
                if status_value == "COMPLETED":
                    order.completed_at = now
                if status_value == "CANCELLED":
                    order.cancelled_at = now
                    order.cancellation_reason = (cancellation_reason or order.cancellation_reason or "").strip() or None
                    await self._release_or_restock_unshipped_order(order, reservation_status="CANCELLED")
                    
                    # Cancel linked outbound document if it exists and is not completed
                    await self._session.execute(
                        text(
                            """
                            UPDATE inventory_documents
                            SET status = 'CANCELLED', updated_at = NOW(), updated_by = :actor_id
                            WHERE order_id = :order_id AND document_type = 'OUTBOUND' AND status != 'COMPLETED'
                            """
                        ),
                        {"order_id": order.id, "actor_id": order.assigned_staff_name or order.user_id},
                    )
                    
                    refund_payment = refund_payment or order.payment_method != "COD"
                if status_value == "REFUNDED":
                    order.refunded_at = now
                    if previous_status not in {"SHIPPED", "RETURNING", "RETURNED", "COMPLETED"}:
                        await self._release_or_restock_unshipped_order(order, reservation_status="RELEASED")
                    refund_payment = True
                if status_value == "PAYMENT_FAILED":
                    order.cancelled_at = now
                    order.payment_status = "FAILED"
                    await self._release_or_restock_unshipped_order(order, reservation_status="EXPIRED")
                if status_value == "RETURNED":
                    await self._restock_order_items(order)

            if cancellation_reason is not None and order.status == "CANCELLED":
                order.cancellation_reason = cancellation_reason.strip() or None

            if refund_payment:
                await self._mark_payment_refunded(order, now=now)

            commerce_repo.save_model(self._session, order)

            if order.status == "COMPLETED" and previous_status != "COMPLETED" and order.user_id and order.loyalty_points_earned > 0:
                user = await commerce_repo.get_user_for_update(self._session, order.user_id)
                if user and user.loyalty_wallet_status == "ACTIVE":
                    balance_before = user.loyalty_points_balance
                    user.loyalty_points_balance += order.loyalty_points_earned
                    user.loyalty_tier = calculate_tier(user.loyalty_points_balance)
                    commerce_repo.save_model(
                        self._session,
                        LoyaltyTransaction(
                            id=uuid4(),
                            user_id=user.id,
                            order_id=order.id,
                            type=LoyaltyTransactionType.EARN,
                            points=order.loyalty_points_earned,
                            balance_before=balance_before,
                            balance_after=user.loyalty_points_balance,
                            reason="Earn points when order is completed.",
                            metadata_json={"order_code": order.order_code},
                        ),
                    )
                    commerce_repo.save_model(self._session, user)

            if order.status in {"CANCELLED", "REFUNDED", "PAYMENT_FAILED"} and previous_status not in {"CANCELLED", "REFUNDED", "PAYMENT_FAILED"} and order.voucher_code:
                voucher = await commerce_repo.get_voucher_by_order_code_for_update(self._session, order.voucher_code)
                if voucher and voucher.refund_policy in {"ALWAYS", "SHOP_FAULT_ONLY"}:
                    await VoucherService(session=self._session).rollback_voucher_usage(order=order)

            if status_value is not None and status_value != previous_status:
                commerce_repo.save_model(
                    self._session,
                    OrderHistoryLog(
                        id=uuid4(),
                        order_id=order.id,
                        old_status=previous_status,
                        new_status=order.status,
                        changed_by=changed_by or "admin-console",
                        note=internal_note or cancellation_reason,
                        metadata_json={
                            "shipping_provider": order.shipping_provider,
                            "tracking_code": order.tracking_code,
                            "refund_payment": refund_payment,
                        },
                    ),
                )
                user = await commerce_repo.get_user(self._session, order.user_id) if order.user_id else None
                self._send_order_status_email(order=order, user=user)
                shipment_events = {
                    "CONFIRMED": [("CONFIRMED", "Đơn hàng đã được xác nhận")],
                    "PAID": [("CONFIRMED", "Đơn hàng đã được xác nhận")],
                    "PROCESSING": [("PACKED", "Đơn hàng đang được đóng gói")],
                    "SHIPPED": [
                        ("HANDED_TO_CARRIER", "Đơn hàng đã bàn giao cho đơn vị vận chuyển"),
                        ("IN_TRANSIT", "Đơn hàng đang được giao"),
                    ],
                    "COMPLETED": [("DELIVERED", "Đơn hàng đã được giao")],
                }
                for event_code, title in shipment_events.get(order.status, []):
                    await self._session.execute(
                        text(
                            """
                            INSERT INTO shipment_events
                                (id, order_id, event_code, title, shipping_provider, tracking_code, source)
                            SELECT :id, :order_id, CAST(:event_code AS VARCHAR), CAST(:title AS VARCHAR), CAST(:provider AS VARCHAR), CAST(:tracking_code AS VARCHAR), 'INTERNAL'
                            WHERE NOT EXISTS (
                                SELECT 1 FROM shipment_events
                                WHERE order_id=:order_id AND event_code=CAST(:event_code AS VARCHAR)
                            )
                            """
                        ),
                        {
                            "id": uuid4(), "order_id": order.id, "event_code": event_code,
                            "title": title, "provider": order.shipping_provider,
                            "tracking_code": order.tracking_code,
                        },
                    )
                if order.user_id:
                    await self._session.execute(
                        text(
                            """
                            INSERT INTO notifications
                                (id, user_id, type, title, message, entity_type, entity_id,
                                 action_url, idempotency_key, available_at)
                            VALUES
                                (:id, :user_id, 'order', 'Cập nhật đơn hàng', :message,
                                 'ORDER', :order_id, :action_url, :key, NOW() + INTERVAL '2 minutes')
                            ON CONFLICT (idempotency_key) WHERE idempotency_key IS NOT NULL DO NOTHING
                            """
                        ),
                        {
                            "id": uuid4(), "user_id": order.user_id, "order_id": order.id,
                            "message": f"Đơn hàng {order.order_code} đã chuyển sang trạng thái {order.status}.",
                            "action_url": f"/orders/{order.id}",
                            "key": f"order:{order.id}:{order.status}",
                        },
                    )

    async def execute_admin_update(self, *, order_id: UUID, request: AdminUpdateOrderRequest) -> None:
        await self.execute(
            order_id=order_id,
            status_value=request.status,
            assigned_staff_name=request.assigned_staff_name,
            internal_note=request.internal_note,
            cancellation_reason=request.cancellation_reason,
            shipping_provider=request.shipping_provider,
            tracking_code=request.tracking_code,
            refund_payment=request.refund_payment,
            changed_by=request.changed_by,
            issue_allocations=request.issue_allocations,
        )

    async def quote_carrier_shipment(self, *, order_id: UUID, provider: str | None = None) -> CarrierShipmentResponse:
        order = await commerce_repo.get_order_for_update(self._session, order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
        item_count = await self._order_item_count(order.id)
        quote = await SandboxShippingPricingService().quote(
            self._session,
            shipping_address=order.shipping_address,
            subtotal_amount=Decimal(order.subtotal_amount or 0),
            item_count=item_count,
            provider=provider or order.shipping_provider,
        )
        return CarrierShipmentResponse(
            order_id=order.id,
            order_code=order.order_code,
            provider=quote.provider,
            tracking_code=order.tracking_code,
            carrier_status="QUOTED",
            shipping_fee=quote.fee,
            estimated_days=quote.estimated_days,
            message=quote.note,
        )

    async def create_carrier_shipment(self, *, order_id: UUID, provider: str | None = None) -> CarrierShipmentResponse:
        async with self._session.begin():
            order = await commerce_repo.get_order_for_update(self._session, order_id)
            if order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
            if order.status in {"CANCELLED", "REFUNDED", "RETURNED"}:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Không thể tạo vận đơn cho đơn đã đóng.")

            shipment = await self._shipping_gateway.register_shipment(
                provider=provider or order.shipping_provider,
                order_code=order.order_code,
                recipient_name=order.recipient_name,
                recipient_phone=order.recipient_phone,
                shipping_address=order.shipping_address,
            )
            order.shipping_provider = shipment.provider or normalize_mock_carrier(provider)
            order.tracking_code = order.tracking_code or shipment.tracking_code
            commerce_repo.save_model(self._session, order)
            await self._insert_shipment_event(
                order=order,
                event_code="CREATED",
                title="Đã tạo vận đơn thử nghiệm",
                description="Vận đơn được tạo bằng mock carrier, không phát sinh giao hàng thật.",
                source="MOCK_CARRIER",
            )
            await self._insert_order_history(
                order=order,
                old_status=order.status,
                new_status=order.status,
                changed_by="mock-carrier",
                note=f"Tạo vận đơn thử nghiệm {order.tracking_code}.",
            )

        return await self.quote_carrier_shipment(order_id=order_id, provider=provider)

    async def cancel_carrier_shipment(self, *, order_id: UUID, reason: str | None = None) -> CarrierShipmentResponse:
        async with self._session.begin():
            order = await commerce_repo.get_order_for_update(self._session, order_id)
            if order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
            if not order.tracking_code:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Đơn hàng chưa có mã vận đơn để huỷ.")
            await self._insert_shipment_event(
                order=order,
                event_code="CANCELLED",
                title="Đã huỷ vận đơn thử nghiệm",
                description=(reason or "Admin huỷ vận đơn trên môi trường mô phỏng.").strip(),
                source="MOCK_CARRIER",
            )
            await self._insert_order_history(
                order=order,
                old_status=order.status,
                new_status=order.status,
                changed_by="mock-carrier",
                note=(reason or "Huỷ vận đơn thử nghiệm.").strip(),
            )
        response = await self.quote_carrier_shipment(order_id=order_id, provider=None)
        response.carrier_status = "CANCELLED"
        response.message = "Đã huỷ vận đơn thử nghiệm; trạng thái đơn hàng không bị đổi tự động."
        return response

    async def update_carrier_event(
        self,
        *,
        order_id: UUID,
        event_code: str,
        note: str | None = None,
    ) -> CarrierShipmentResponse:
        titles = {
            "CREATED": "Đã tạo vận đơn thử nghiệm",
            "HANDED_TO_CARRIER": "Đơn hàng đã bàn giao cho đơn vị vận chuyển",
            "IN_TRANSIT": "Đơn hàng đang được giao",
            "DELIVERED": "Đơn hàng đã được giao",
            "DELIVERY_FAILED": "Giao hàng không thành công",
            "CANCELLED": "Đã huỷ vận đơn thử nghiệm",
        }
        if event_code not in titles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trạng thái vận chuyển không hợp lệ.")
        async with self._session.begin():
            order = await commerce_repo.get_order_for_update(self._session, order_id)
            if order is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng.")
            if not order.tracking_code:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Đơn hàng chưa có mã vận đơn.")
            await self._insert_shipment_event(
                order=order,
                event_code=event_code,
                title=titles[event_code],
                description=note,
                source="MOCK_CARRIER",
            )
            await self._insert_order_history(
                order=order,
                old_status=order.status,
                new_status=order.status,
                changed_by="mock-carrier",
                note=note or titles[event_code],
            )
        response = await self.quote_carrier_shipment(order_id=order_id, provider=None)
        response.carrier_status = event_code
        response.message = titles[event_code]
        return response

    async def _order_item_count(self, order_id: UUID) -> int:
        result = await self._session.execute(
            text("SELECT COALESCE(SUM(quantity), 0)::int FROM order_items WHERE order_id = :order_id"),
            {"order_id": order_id},
        )
        return max(1, int(result.scalar() or 1))

    async def _insert_shipment_event(
        self,
        *,
        order: Order,
        event_code: str,
        title: str,
        description: str | None = None,
        source: str = "MOCK_CARRIER",
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO shipment_events
                    (id, order_id, event_code, title, description, shipping_provider, tracking_code, source)
                SELECT :id, :order_id, CAST(:event_code AS VARCHAR), CAST(:title AS VARCHAR), CAST(:description AS VARCHAR), CAST(:provider AS VARCHAR), CAST(:tracking_code AS VARCHAR), CAST(:source AS VARCHAR)
                WHERE NOT EXISTS (
                    SELECT 1 FROM shipment_events
                    WHERE order_id = :order_id
                      AND event_code = CAST(:event_code AS VARCHAR)
                      AND COALESCE(tracking_code, '') = COALESCE(CAST(:tracking_code AS VARCHAR), '')
                      AND source = CAST(:source AS VARCHAR)
                )
                """
            ),
            {
                "id": uuid4(),
                "order_id": order.id,
                "event_code": event_code,
                "title": title,
                "description": description,
                "provider": order.shipping_provider,
                "tracking_code": order.tracking_code,
                "source": source,
            },
        )

    def _insert_order_history(
        self,
        *,
        order: Order,
        old_status: str,
        new_status: str,
        changed_by: str,
        note: str | None = None,
    ) -> None:
        commerce_repo.save_model(
            self._session,
            OrderHistoryLog(
                id=uuid4(),
                order_id=order.id,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
                note=note,
                metadata_json={
                    "shipping_provider": order.shipping_provider,
                    "tracking_code": order.tracking_code,
                },
            ),
        )

    async def expire_pending_orders(self, *, online_timeout_minutes: int = 15, cod_timeout_hours: int = 24) -> int:
        order_ids = await commerce_repo.list_pending_order_ids_to_expire(
            self._session,
            online_timeout_minutes=online_timeout_minutes,
            cod_timeout_hours=cod_timeout_hours,
        )
        expired_count = 0
        for order_id in order_ids:
            await self.execute(
                order_id=order_id,
                status_value="PAYMENT_FAILED",
                internal_note="Auto cancel overdue pending order.",
                changed_by="system-expirer",
            )
            expired_count += 1
        return expired_count

    async def _mark_payment_refunded(self, order: Order, *, now: datetime) -> None:
        transactions = await commerce_repo.list_payment_transactions_for_update(self._session, order.id)
        if not transactions:
            return
        for transaction in transactions:
            if transaction.status == "REFUNDED":
                continue
            if transaction.status in {"PAID", "PENDING"}:
                gateway_result = await self._refund_gateway.refund(
                    provider=transaction.provider,
                    order_code=order.order_code,
                    amount=Decimal(transaction.amount or 0),
                )
                transaction.status = "REFUNDED"
                transaction.raw_response = {
                    **(transaction.raw_response or {}),
                    "refund_marked_at": now.isoformat(),
                    "refund_mode": gateway_result.mode,
                    "refund_provider_ref": gateway_result.provider_ref,
                    "refund_message": gateway_result.message,
                }
                commerce_repo.save_model(self._session, transaction)
        order.payment_status = "REFUNDED"
        order.refunded_at = order.refunded_at or now

    async def _release_or_restock_unshipped_order(self, order: Order, *, reservation_status: str) -> None:
        if await commerce_repo.order_has_inventory_adjustment_reason(
            self._session,
            order_code=order.order_code,
            reason="ORDER_CREATED",
        ):
            await self._restock_order_items(order)
            return
        await commerce_repo.close_active_order_reservations(
            self._session,
            order_id=order.id,
            status=reservation_status,
        )

    async def _ship_order_items(self, order: Order, *, issue_allocations: list | None = None) -> None:
        if await commerce_repo.order_has_inventory_adjustment_reason(
            self._session,
            order_code=order.order_code,
            reason="ORDER_SHIPPED",
        ):
            return
        if await commerce_repo.order_has_inventory_adjustment_reason(
            self._session,
            order_code=order.order_code,
            reason="ORDER_CREATED",
        ):
            await commerce_repo.close_active_order_reservations(
                self._session,
                order_id=order.id,
                status="CONSUMED",
            )
            return

        allocations_by_item_id: dict[str, list[dict]] = {}
        for allocation in issue_allocations or []:
            if isinstance(allocation, dict):
                order_item_id_value = allocation.get("order_item_id") or allocation.get("orderItemId")
                location_id_value = allocation.get("location_id") or allocation.get("locationId")
                quantity_value = allocation.get("quantity")
            else:
                order_item_id_value = getattr(allocation, "order_item_id", None)
                location_id_value = getattr(allocation, "location_id", None)
                quantity_value = getattr(allocation, "quantity", None)
            order_item_id = str(order_item_id_value or "")
            if not order_item_id:
                continue
            allocations_by_item_id.setdefault(order_item_id, []).append(
                {
                    "location_id": location_id_value,
                    "quantity": int(quantity_value or 0),
                }
            )

        for item in await commerce_repo.list_restock_items(self._session, order_id=order.id, order_code=order.order_code):
            quantity = int(item["quantity"] or 0)
            variant_id = item["order_variant_id"] or item["variant_id"]
            manual_allocations = allocations_by_item_id.get(str(item["id"]), [])
            if manual_allocations and sum(int(allocation.get("quantity") or 0) for allocation in manual_allocations) != quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dòng {item['product_name']}: tổng số lượng xác nhận kệ phải bằng số lượng cần xuất.",
                )
            if manual_allocations:
                location_ids = [str(allocation.get("location_id") or "") for allocation in manual_allocations]
                if any(not location_id for location_id in location_ids) or len(set(location_ids)) != len(location_ids):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Dòng {item['product_name']}: kệ xác nhận không hợp lệ hoặc bị trùng.",
                    )
            if variant_id:
                inventory_row = await commerce_repo.get_variant_stock_for_update(self._session, variant_id)
                if not inventory_row:
                    continue
                old_quantity = int(inventory_row["stock_quantity"] or 0)
                new_quantity = old_quantity - quantity
                if new_quantity < 0:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Not enough stock for {item['product_name']}.")
                await commerce_repo.update_variant_stock(self._session, variant_id=variant_id, quantity=new_quantity)
                try:
                    if manual_allocations:
                        allocations = await commerce_repo.deduct_inventory_levels_from_locations(
                            self._session,
                            product_id=inventory_row["product_id"],
                            variant_id=variant_id,
                            location_quantities=manual_allocations,
                        )
                    else:
                        allocations = await commerce_repo.deduct_inventory_levels_fifo(
                            self._session,
                            product_id=inventory_row["product_id"],
                            variant_id=variant_id,
                            quantity=quantity,
                        )
                except ValueError as exc:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
                for allocation in allocations:
                    try:
                        await commerce_repo.consume_inventory_lots_fifo(
                            self._session,
                            product_id=inventory_row["product_id"],
                            variant_id=variant_id,
                            location_id=allocation["locationId"],
                            quantity=int(allocation["quantity"]),
                            reference_code=order.order_code,
                            order_id=order.id,
                        )
                    except ValueError as exc:
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
                    await self._session.execute(
                        text(
                            """
                            UPDATE product_imeis
                            SET status = 'SOLD', sold_at = NOW(), sold_order_id = :order_id, updated_at = NOW()
                            WHERE id IN (
                                SELECT id FROM product_imeis
                                WHERE product_id = :product_id
                                  AND (variant_id IS NOT DISTINCT FROM :variant_id)
                                  AND location_id = :location_id
                                  AND status = 'IN_STOCK'
                                ORDER BY received_at ASC
                                LIMIT :quantity
                                FOR UPDATE
                            )
                            """
                        ),
                        {
                            "order_id": order.id,
                            "product_id": inventory_row["product_id"],
                            "variant_id": variant_id,
                            "location_id": allocation["locationId"],
                            "quantity": int(allocation["quantity"]),
                        },
                    )
                    await commerce_repo.insert_inventory_adjustment(
                        self._session,
                        product_id=inventory_row["product_id"],
                        variant_id=variant_id,
                        old_quantity=int(allocation["oldQuantity"]),
                        new_quantity=int(allocation["newQuantity"]),
                        delta=-int(allocation["quantity"]),
                        transaction_type="SALE",
                        reference_code=order.order_code,
                        reason="ORDER_SHIPPED",
                        note=f"Xuất kho khi giao đơn hàng cho {item['product_name']}.",
                        location_code=allocation.get("locationCode"),
                        location_name=allocation.get("locationName"),
                    )
                continue

            if not item["product_id"]:
                continue
            inventory_row = await commerce_repo.get_product_stock_for_update(self._session, item["product_id"])
            if not inventory_row:
                continue
            old_quantity = int(inventory_row["stock_quantity"] or 0)
            new_quantity = old_quantity - quantity
            if new_quantity < 0:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Not enough stock for {item['product_name']}.")
            await commerce_repo.update_product_stock(self._session, product_id=item["product_id"], quantity=new_quantity)
            try:
                if manual_allocations:
                    allocations = await commerce_repo.deduct_inventory_levels_from_locations(
                        self._session,
                        product_id=item["product_id"],
                        variant_id=None,
                        location_quantities=manual_allocations,
                    )
                else:
                    allocations = await commerce_repo.deduct_inventory_levels_fifo(
                        self._session,
                        product_id=item["product_id"],
                        variant_id=None,
                        quantity=quantity,
                    )
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
            for allocation in allocations:
                try:
                    await commerce_repo.consume_inventory_lots_fifo(
                        self._session,
                        product_id=item["product_id"],
                        variant_id=None,
                        location_id=allocation["locationId"],
                        quantity=int(allocation["quantity"]),
                        reference_code=order.order_code,
                        order_id=order.id,
                    )
                except ValueError as exc:
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
                await self._session.execute(
                    text(
                        """
                        UPDATE product_imeis
                        SET status = 'SOLD', sold_at = NOW(), sold_order_id = :order_id, updated_at = NOW()
                        WHERE id IN (
                            SELECT id FROM product_imeis
                            WHERE product_id = :product_id
                              AND variant_id IS NULL
                              AND location_id = :location_id
                              AND status = 'IN_STOCK'
                            ORDER BY received_at ASC
                            LIMIT :quantity
                            FOR UPDATE
                        )
                        """
                    ),
                    {
                        "order_id": order.id,
                        "product_id": item["product_id"],
                        "location_id": allocation["locationId"],
                        "quantity": int(allocation["quantity"]),
                    },
                )
                await commerce_repo.insert_inventory_adjustment(
                    self._session,
                    product_id=item["product_id"],
                    variant_id=None,
                    old_quantity=int(allocation["oldQuantity"]),
                    new_quantity=int(allocation["newQuantity"]),
                    delta=-int(allocation["quantity"]),
                    transaction_type="SALE",
                    reference_code=order.order_code,
                    reason="ORDER_SHIPPED",
                    note=f"Xuất kho khi giao đơn hàng cho {item['product_name']}.",
                    location_code=allocation.get("locationCode"),
                    location_name=allocation.get("locationName"),
                )

        await commerce_repo.close_active_order_reservations(
            self._session,
            order_id=order.id,
            status="CONSUMED",
        )

    async def _restock_order_items(self, order: Order) -> None:
        for item in await commerce_repo.list_restock_items(self._session, order_id=order.id, order_code=order.order_code):
            quantity = int(item["quantity"] or 0)
            variant_id = item["order_variant_id"] or item["variant_id"]
            if variant_id:
                inventory_row = await commerce_repo.get_variant_stock_for_update(self._session, variant_id)
                if not inventory_row:
                    continue
                old_quantity = int(inventory_row["stock_quantity"] or 0)
                new_quantity = old_quantity + quantity
                await commerce_repo.update_variant_stock(self._session, variant_id=variant_id, quantity=new_quantity)
                await commerce_repo.insert_inventory_adjustment(
                    self._session,
                    product_id=inventory_row["product_id"],
                    variant_id=variant_id,
                    old_quantity=old_quantity,
                    new_quantity=new_quantity,
                    delta=quantity,
                    transaction_type="RETURN",
                    reference_code=order.order_code,
                    reason="ORDER_CANCELLED_RESTOCK",
                    note=f"Restock after cancelling order for {item['product_name']}.",
                )
                continue

            if not item["product_id"]:
                continue
            inventory_row = await commerce_repo.get_product_stock_for_update(self._session, item["product_id"])
            if not inventory_row:
                continue
            old_quantity = int(inventory_row["stock_quantity"] or 0)
            new_quantity = old_quantity + quantity
            await commerce_repo.update_product_stock(self._session, product_id=item["product_id"], quantity=new_quantity)
            await commerce_repo.insert_inventory_adjustment(
                self._session,
                product_id=item["product_id"],
                variant_id=None,
                old_quantity=old_quantity,
                new_quantity=new_quantity,
                delta=quantity,
                transaction_type="RETURN",
                reference_code=order.order_code,
                reason="ORDER_CANCELLED_RESTOCK",
                note=f"Restock after cancelling order for {item['product_name']}.",
            )
        # Giải phóng các IMEI liên quan đến đơn hàng này về trạng thái sẵn sàng
        await self._session.execute(
            text(
                """
                UPDATE product_imeis
                SET status = 'IN_STOCK', sold_at = NULL, sold_order_id = NULL, updated_at = NOW()
                WHERE sold_order_id = :order_id AND status = 'SOLD'
                """
            ),
            {"order_id": order.id},
        )

    def _send_order_status_email(self, *, order: Order, user: User | None) -> None:
        if not user or not user.email or not settings.smtp_username or not settings.smtp_password:
            return
        sender = settings.smtp_from_email or settings.smtp_username
        status_label = ORDER_STATUS_EMAIL_LABELS.get(order.status, order.status)
        recipient_name = user.full_name or order.recipient_name or user.email
        subject = f"Cap nhat don hang {order.order_code} - {status_label}"
        plain_lines = [
            f"Xin chao {recipient_name},",
            "",
            f"Don hang {order.order_code} cua ban vua duoc cap nhat sang trang thai: {status_label}.",
            f"Tong thanh toan: {Decimal(order.total_amount or 0):,.0f} VND.",
            f"Phuong thuc thanh toan: {order.payment_method}.",
        ]
        if order.tracking_code:
            plain_lines.append(f"Ma van don: {order.tracking_code}")
        if order.shipping_provider:
            plain_lines.append(f"Don vi van chuyen: {order.shipping_provider}")
        if order.status == "CANCELLED" and order.cancellation_reason:
            plain_lines.append(f"Ly do huy: {order.cancellation_reason}")
        plain_lines.extend(["", "Cam on ban da mua sam cung ElectroMart VietNam."])

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = user.email
        message.set_content("\n".join(plain_lines))
        message.add_alternative(
            f"""
            <div style="font-family:Arial,sans-serif;line-height:1.6;color:#111827">
              <h2 style="color:#d70018">Cap nhat don hang {order.order_code}</h2>
              <p>Xin chao <strong>{recipient_name}</strong>,</p>
              <p>Don hang cua ban vua duoc cap nhat sang trang thai <strong>{status_label}</strong>.</p>
              <p><strong>Tong thanh toan:</strong> {Decimal(order.total_amount or 0):,.0f} VND</p>
              <p><strong>Thanh toan:</strong> {order.payment_method}</p>
              {f'<p><strong>Don vi van chuyen:</strong> {order.shipping_provider}</p>' if order.shipping_provider else ''}
              {f'<p><strong>Ma van don:</strong> {order.tracking_code}</p>' if order.tracking_code else ''}
              {f'<p><strong>Ly do huy:</strong> {order.cancellation_reason}</p>' if order.status == 'CANCELLED' and order.cancellation_reason else ''}
              <p style="margin-top:16px">Cam on ban da mua sam cung ElectroMart VietNam.</p>
            </div>
            """,
            subtype="html",
        )
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        except Exception:
            return


class ReportUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def revenue(self) -> RevenueReportResponse:
        report = await commerce_repo.get_revenue_report(self._session)
        return RevenueReportResponse(
            total_orders=report["total_orders"],
            completed_orders=report["completed_orders"],
            total_revenue=report["total_revenue"],
            ai_interactions=report["ai_interactions"],
            loyalty_points_used=report["loyalty_points_used"],
        )


class ShippingQuoteUseCase:
    def __init__(self) -> None:
        self._shipping_pricing = SandboxShippingPricingService()

    async def execute(
        self,
        session: AsyncSession,
        *,
        shipping_address: str,
        subtotal_amount: Decimal,
        item_count: int,
        provider: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ShippingQuoteResponse:
        quote = await self._shipping_pricing.quote(
            session,
            shipping_address=shipping_address,
            subtotal_amount=subtotal_amount,
            item_count=item_count,
            provider=provider,
            lat=lat,
            lng=lng,
        )

        return ShippingQuoteResponse(
            shipping_fee=quote.fee,
            zone=quote.zone,
            estimated_days=quote.estimated_days,
            free_shipping_applied=quote.free_shipping_applied,
            provider=quote.provider,
            service_name=quote.service_name,
            note=quote.note,
        )
