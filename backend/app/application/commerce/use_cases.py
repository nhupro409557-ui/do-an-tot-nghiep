from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.message import EmailMessage
import smtplib
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.commerce.integrations import RefundGateway, ShippingGateway
from app.application.commerce.integrations import MoMoSandboxGateway, SandboxShippingPricingService
from app.application.commerce.schemas import (
    AdminUpdateOrderRequest,
    CreateOrderRequest,
    CreateOrderResponse,
    RevenueReportResponse,
    ShippingQuoteResponse,
    UserVoucherResponse,
    VoucherValidationResponse,
)
from app.config import settings


ORDER_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"PAID", "PROCESSING", "CANCELLED", "PAYMENT_FAILED"},
    "CONFIRMED": {"PROCESSING", "CANCELLED"},
    "PAID": {"PROCESSING", "CANCELLED", "REFUNDED", "PAYMENT_FAILED"},
    "PROCESSING": {"SHIPPED", "CANCELLED", "PAYMENT_FAILED"},
    "SHIPPED": {"COMPLETED", "REFUNDED", "RETURNING"},
    "COMPLETED": {"RETURNING"},
    "CANCELLED": set(),
    "REFUNDED": set(),
    "PAYMENT_FAILED": set(),
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
from app.domain.users.entities import LoyaltyTransactionType
from app.infrastructure.database.models import (
    AIContextLog,
    LoyaltyTransaction,
    Order,
    OrderHistoryLog,
    OrderItem,
    PaymentTransaction,
    Product,
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
    product_ids: set[str] = field(default_factory=set)
    category_ids: set[str] = field(default_factory=set)
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
        if voucher.eligible_user_registered_after and context.user_id:
            user_result = await service._session.execute(select(User.created_at).where(User.id == context.user_id))
            registered_at = user_result.scalar_one_or_none()
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
        return None


class VoucherService:
    # Rule pipeline keeps the voucher policy modular so future business rules can be added safely.
    _rules: tuple[VoucherRule, ...] = (
        VoucherActiveWindowRule(),
        VoucherWalletRule(),
        MinOrderRule(),
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
        product_ids: set[str] | None = None,
        category_ids: set[str] | None = None,
    ) -> VoucherValidationResponse:
        voucher = await self._get_active_voucher(code)
        if voucher is None:
            return self._invalid(code.upper(), "VOUCHER_ERR_INVALID", "Voucher is invalid or inactive.")

        now_result = await self._session.execute(text("SELECT NOW()"))
        now = now_result.scalar_one()
        context = VoucherValidationContext(
            voucher=voucher,
            now=now,
            subtotal_amount=subtotal_amount,
            user_id=user_id,
            user_tier=user_tier,
            abandoned_cart_recovery=abandoned_cart_recovery,
            device_id=device_id,
            ip_address=ip_address,
            product_ids=product_ids or set(),
            category_ids=category_ids or set(),
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
        voucher = await self._session.scalar(select(Voucher).where(Voucher.id == voucher_id))
        if voucher is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voucher not found.")
        if voucher.status != "ACTIVE":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Voucher is not active.")

        existing = await self._session.scalar(
            select(UserVoucher)
            .where(UserVoucher.user_id == user_id)
            .where(UserVoucher.voucher_id == voucher_id)
            .where(UserVoucher.status.in_(["AVAILABLE", "RESERVED", "USED"]))
        )
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
        self._session.add(wallet_voucher)
        await self._session.flush()
        return self._wallet_response(wallet_voucher, voucher)

    async def list_user_vouchers(self, *, user_id: UUID) -> list[UserVoucherResponse]:
        result = await self._session.execute(
            select(UserVoucher, Voucher)
            .join(Voucher, Voucher.id == UserVoucher.voucher_id)
            .where(UserVoucher.user_id == user_id)
            .order_by(UserVoucher.claimed_at.desc())
        )
        responses: list[UserVoucherResponse] = []
        now = datetime.now(timezone.utc)
        for wallet_voucher, voucher in result.all():
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
            claimed_voucher = await self._session.scalar(
                select(UserVoucher)
                .where(UserVoucher.user_id == user_id)
                .where(UserVoucher.voucher_id == voucher.id)
                .where(UserVoucher.status.in_(["AVAILABLE", "RESERVED"]))
                .order_by(UserVoucher.claimed_at.desc())
                .with_for_update()
            )
        voucher.used_count += 1
        voucher.total_discount_used = Decimal(voucher.total_discount_used or 0) + discount_amount
        self._session.add(voucher)
        if claimed_voucher is not None:
            claimed_voucher.status = "USED"
            claimed_voucher.used_at = datetime.now(timezone.utc)
            claimed_voucher.order_id = order_id
            self._session.add(claimed_voucher)
        return claimed_voucher

    async def rollback_voucher_usage(self, *, order: Order) -> None:
        if not order.voucher_code:
            return
        voucher = await self._session.scalar(
            select(Voucher).where(Voucher.code == order.voucher_code.upper()).with_for_update()
        )
        if voucher is not None:
            voucher.used_count = max(0, int(voucher.used_count or 0) - 1)
            restored_discount = min(
                Decimal(voucher.total_discount_used or 0),
                Decimal(order.discount_amount or 0),
            )
            voucher.total_discount_used = max(Decimal("0"), Decimal(voucher.total_discount_used or 0) - restored_discount)
            self._session.add(voucher)
        if order.voucher_claim_id:
            wallet_voucher = await self._session.scalar(
                select(UserVoucher).where(UserVoucher.id == order.voucher_claim_id).with_for_update()
            )
            if wallet_voucher is not None:
                now = datetime.now(timezone.utc)
                if wallet_voucher.expires_at and wallet_voucher.expires_at < now:
                    wallet_voucher.status = "EXPIRED"
                else:
                    wallet_voucher.status = "AVAILABLE"
                wallet_voucher.used_at = None
                wallet_voucher.order_id = None
                self._session.add(wallet_voucher)

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
        self._session.add(wallet_voucher)

    async def _get_active_voucher(self, code: str) -> Voucher | None:
        result = await self._session.execute(
            select(Voucher).where(Voucher.code == code.upper()).where(Voucher.status == "ACTIVE")
        )
        return result.scalar_one_or_none()

    async def _get_claimed_voucher(self, *, user_id: UUID, voucher_id: UUID) -> UserVoucher | None:
        result = await self._session.execute(
            select(UserVoucher)
            .where(UserVoucher.user_id == user_id)
            .where(UserVoucher.voucher_id == voucher_id)
            .order_by(UserVoucher.claimed_at.desc())
        )
        return result.scalar_one_or_none()

    async def _user_order_count(self, user_id: UUID) -> int:
        result = await self._session.execute(
            text("SELECT COUNT(*) FROM orders WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        return int(result.scalar() or 0)

    async def _user_voucher_usage_count(self, user_id: UUID, code: str) -> int:
        result = await self._session.execute(
            text("SELECT COUNT(*) FROM orders WHERE user_id = :user_id AND voucher_code = :code"),
            {"user_id": user_id, "code": code.upper()},
        )
        return int(result.scalar() or 0)

    async def _voucher_usage_count_by(self, column: str, value: str, code: str) -> int:
        if column not in {"voucher_device_id", "voucher_ip_address"}:
            return 0
        result = await self._session.execute(
            text(f"SELECT COUNT(*) FROM orders WHERE voucher_code = :code AND {column} = :value"),
            {"code": code.upper(), "value": value},
        )
        return int(result.scalar() or 0)

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

    async def execute(self, request: CreateOrderRequest) -> CreateOrderResponse:
        if request.idempotency_key:
            existing = await self._session.scalar(select(Order).where(Order.idempotency_key == request.idempotency_key))
            if existing is not None:
                return CreateOrderResponse(
                    order_id=existing.id,
                    order_code=existing.order_code,
                    payment_method=existing.payment_method,
                    payment_status=existing.payment_status,
                    shipping_fee=Decimal(existing.shipping_fee or 0),
                    total_amount=Decimal(existing.total_amount or 0),
                    loyalty_points_earned=int(existing.loyalty_points_earned or 0),
                    checkout_url=await self._existing_checkout_url(existing.id),
                )

        subtotal = sum(item.unit_price * item.quantity for item in request.items)
        shipping_quote = self._shipping_pricing.quote(
            shipping_address=request.shipping.shipping_address,
            subtotal_amount=subtotal,
            item_count=sum(item.quantity for item in request.items),
        )
        voucher_discount = Decimal("0")
        wallet_claim_id: UUID | None = None

        async with self._session.begin():
            user = None
            if request.user_id:
                user = await self._session.scalar(select(User).where(User.id == request.user_id).with_for_update())
                if user is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
                if user.loyalty_wallet_status != "ACTIVE":
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Loyalty wallet is not active.")
                if request.loyalty_points_used > user.loyalty_points_balance:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient loyalty points.")

            product_ids = {str(item.product_id) for item in request.items if item.product_id}
            category_ids = {str(item.category_id) for item in request.items if item.category_id}
            if product_ids and not category_ids:
                product_result = await self._session.execute(
                    select(Product.id, Product.category_id, Product.subcategory_id).where(
                        Product.id.in_([UUID(item) for item in product_ids])
                    )
                )
                category_ids = {
                    str(row.subcategory_id or row.category_id)
                    for row in product_result
                    if row.subcategory_id or row.category_id
                }

            voucher = None
            voucher_service = VoucherService(session=self._session)
            if request.voucher_code:
                voucher = await self._session.scalar(
                    select(Voucher)
                    .where(Voucher.code == request.voucher_code.upper())
                    .where(Voucher.status == "ACTIVE")
                    .with_for_update()
                )
                if voucher is None:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid voucher.")
                validation = await voucher_service.validate(
                    code=voucher.code,
                    subtotal_amount=subtotal,
                    user_id=request.user_id,
                    user_tier=user.loyalty_tier if user else None,
                    device_id=request.voucher_device_id,
                    ip_address=request.voucher_ip_address,
                    product_ids=product_ids,
                    category_ids=category_ids,
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
            order_code = f"EC{uuid4().hex[:10].upper()}"

            for item in request.items:
                if item.variant_id:
                    inventory_row = (
                        await self._session.execute(
                            text(
                                """
                                SELECT id, product_id, stock_quantity
                                FROM product_variants
                                WHERE id = :variant_id
                                  AND (:product_id IS NULL OR product_id = :product_id)
                                  AND is_active = TRUE
                                FOR UPDATE
                                """
                            ),
                            {"variant_id": item.variant_id, "product_id": item.product_id},
                        )
                    ).mappings().first()
                    if not inventory_row:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found.")
                    old_quantity = int(inventory_row["stock_quantity"] or 0)
                    new_quantity = old_quantity - item.quantity
                    if new_quantity < 0:
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Not enough stock for {item.product_name}.")
                    await self._session.execute(
                        text("UPDATE product_variants SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
                        {"id": item.variant_id, "quantity": new_quantity},
                    )
                    await self._session.execute(
                        text(
                            """
                            INSERT INTO inventory_adjustment_logs (
                                id, product_id, variant_id, old_quantity, new_quantity, delta,
                                transaction_type, reference_code, reason, note
                            )
                            VALUES (
                                :id, :product_id, :variant_id, :old_quantity, :new_quantity, :delta,
                                'SALE', :reference_code, 'ORDER_CREATED', :note
                            )
                            """
                        ),
                        {
                            "id": uuid4(),
                            "product_id": item.product_id or inventory_row["product_id"],
                            "variant_id": item.variant_id,
                            "old_quantity": old_quantity,
                            "new_quantity": new_quantity,
                            "delta": -item.quantity,
                            "reference_code": order_code,
                            "note": f"Reserve stock during checkout for {item.product_name}.",
                        },
                    )
                elif item.product_id:
                    inventory_row = (
                        await self._session.execute(
                            text(
                                """
                                SELECT id, stock_quantity
                                FROM products
                                WHERE id = :product_id AND status = 'ACTIVE'
                                FOR UPDATE
                                """
                            ),
                            {"product_id": item.product_id},
                        )
                    ).mappings().first()
                    if not inventory_row:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
                    old_quantity = int(inventory_row["stock_quantity"] or 0)
                    new_quantity = old_quantity - item.quantity
                    if new_quantity < 0:
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Not enough stock for {item.product_name}.")
                    await self._session.execute(
                        text("UPDATE products SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
                        {"id": item.product_id, "quantity": new_quantity},
                    )
                    await self._session.execute(
                        text(
                            """
                            INSERT INTO inventory_adjustment_logs (
                                id, product_id, variant_id, old_quantity, new_quantity, delta,
                                transaction_type, reference_code, reason, note
                            )
                            VALUES (
                                :id, :product_id, NULL, :old_quantity, :new_quantity, :delta,
                                'SALE', :reference_code, 'ORDER_CREATED', :note
                            )
                            """
                        ),
                        {
                            "id": uuid4(),
                            "product_id": item.product_id,
                            "old_quantity": old_quantity,
                            "new_quantity": new_quantity,
                            "delta": -item.quantity,
                            "reference_code": order_code,
                            "note": f"Reserve stock during checkout for {item.product_name}.",
                        },
                    )

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
                status="PENDING",
                payment_method=request.payment_method,
                payment_status="UNPAID" if request.payment_method == "COD" else "PENDING",
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
                shipping_address=request.shipping.shipping_address,
            )
            self._session.add(order)
            self._session.add(
                OrderHistoryLog(
                    id=uuid4(),
                    order_id=order.id,
                    old_status=None,
                    new_status=order.status,
                    changed_by="system-checkout",
                    note="Order created from checkout.",
                    metadata_json={"payment_method": order.payment_method},
                )
            )

            for item in request.items:
                self._session.add(
                    OrderItem(
                        id=uuid4(),
                        order_id=order.id,
                        product_id=item.product_id,
                        product_name=item.product_name,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        total_price=item.unit_price * item.quantity,
                    )
                )

            checkout_url = None
            if request.payment_method != "COD":
                payment_init = None
                if request.payment_method == "MOMO":
                    payment_init = await self._momo_gateway.create_payment(
                        order_code=order.order_code,
                        amount=total,
                        order_info=f"Thanh toan don hang {order.order_code}",
                        extra_data={"orderCode": order.order_code, "userId": str(request.user_id) if request.user_id else ""},
                    )
                    checkout_url = payment_init.checkout_url
                else:
                    checkout_url = f"https://sandbox-payment.local/{request.payment_method.lower()}/{order.order_code}"
                self._session.add(
                    PaymentTransaction(
                        id=uuid4(),
                        order_id=order.id,
                        provider=request.payment_method,
                        amount=total,
                        status="PENDING",
                        transaction_ref=order.order_code,
                        checkout_url=checkout_url,
                        raw_response=(payment_init.raw_response if payment_init else {"mode": "sandbox"}),
                    )
                )

            if user and request.loyalty_points_used > 0:
                balance_before = user.loyalty_points_balance
                user.loyalty_points_balance -= request.loyalty_points_used
                self._session.add(
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
                    )
                )
                self._session.add(user)

        return CreateOrderResponse(
            order_id=order.id,
            order_code=order.order_code,
            payment_method=order.payment_method,
            payment_status=order.payment_status,
            shipping_fee=shipping_quote.fee,
            total_amount=total,
            loyalty_points_earned=earned_points,
            checkout_url=checkout_url,
        )

    async def _existing_checkout_url(self, order_id: UUID) -> str | None:
        result = await self._session.execute(
            select(PaymentTransaction.checkout_url).where(PaymentTransaction.order_id == order_id).limit(1)
        )
        return result.scalar_one_or_none()


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
    ) -> None:
        async with self._session.begin():
            order = await self._session.scalar(select(Order).where(Order.id == order_id).with_for_update())
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
                if status_value == "SHIPPED":
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
                    await self._restock_order_items(order)
                    refund_payment = refund_payment or order.payment_method != "COD"
                if status_value == "REFUNDED":
                    order.refunded_at = now
                    refund_payment = True
                if status_value == "PAYMENT_FAILED":
                    order.cancelled_at = now
                    order.payment_status = "FAILED"
                    await self._restock_order_items(order)
                if status_value == "RETURNED":
                    await self._restock_order_items(order)

            if cancellation_reason is not None and order.status == "CANCELLED":
                order.cancellation_reason = cancellation_reason.strip() or None

            if refund_payment:
                await self._mark_payment_refunded(order, now=now)

            self._session.add(order)

            if order.status == "COMPLETED" and previous_status != "COMPLETED" and order.user_id and order.loyalty_points_earned > 0:
                user = await self._session.scalar(select(User).where(User.id == order.user_id).with_for_update())
                if user and user.loyalty_wallet_status == "ACTIVE":
                    balance_before = user.loyalty_points_balance
                    user.loyalty_points_balance += order.loyalty_points_earned
                    user.loyalty_tier = calculate_tier(user.loyalty_points_balance)
                    self._session.add(
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
                        )
                    )
                    self._session.add(user)

            if order.status in {"CANCELLED", "REFUNDED", "PAYMENT_FAILED"} and previous_status not in {"CANCELLED", "REFUNDED", "PAYMENT_FAILED"} and order.voucher_code:
                voucher = await self._session.scalar(
                    select(Voucher).where(Voucher.code == order.voucher_code.upper()).with_for_update()
                )
                if voucher and voucher.refund_policy in {"ALWAYS", "SHOP_FAULT_ONLY"}:
                    await VoucherService(session=self._session).rollback_voucher_usage(order=order)

            if status_value is not None and status_value != previous_status:
                self._session.add(
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
                    )
                )
                user = await self._session.scalar(select(User).where(User.id == order.user_id)) if order.user_id else None
                self._send_order_status_email(order=order, user=user)

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
        )

    async def expire_pending_orders(self, *, online_timeout_minutes: int = 15, cod_timeout_hours: int = 24) -> int:
        result = await self._session.execute(
            text(
                """
                SELECT id
                FROM orders
                WHERE status = 'PENDING'
                  AND (
                    (payment_method <> 'COD' AND created_at < NOW() - make_interval(mins => :online_timeout_minutes))
                    OR
                    (payment_method = 'COD' AND created_at < NOW() - make_interval(hours => :cod_timeout_hours))
                  )
                ORDER BY created_at ASC
                """
            ),
            {"online_timeout_minutes": online_timeout_minutes, "cod_timeout_hours": cod_timeout_hours},
        )
        expired_count = 0
        for row in result.all():
            await self.execute(
                order_id=row[0],
                status_value="PAYMENT_FAILED",
                internal_note="Auto cancel overdue pending order.",
                changed_by="system-expirer",
            )
            expired_count += 1
        return expired_count

    async def _mark_payment_refunded(self, order: Order, *, now: datetime) -> None:
        payment_rows = await self._session.execute(
            select(PaymentTransaction).where(PaymentTransaction.order_id == order.id).with_for_update()
        )
        transactions = payment_rows.scalars().all()
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
                self._session.add(transaction)
        order.payment_status = "REFUNDED"
        order.refunded_at = order.refunded_at or now

    async def _restock_order_items(self, order: Order) -> None:
        item_rows = await self._session.execute(
            text(
                """
                SELECT
                    oi.id,
                    oi.product_id,
                    oi.product_name,
                    oi.quantity,
                    logs.variant_id
                FROM order_items oi
                LEFT JOIN LATERAL (
                    SELECT ial.variant_id
                    FROM inventory_adjustment_logs ial
                    WHERE ial.reference_code = :reference_code
                      AND ial.product_id IS NOT DISTINCT FROM oi.product_id
                      AND ial.reason = 'ORDER_CREATED'
                    ORDER BY ial.created_at ASC
                    LIMIT 1
                ) logs ON TRUE
                WHERE oi.order_id = :order_id
                """
            ),
            {"order_id": order.id, "reference_code": order.order_code},
        )
        for item in item_rows.mappings().all():
            quantity = int(item["quantity"] or 0)
            variant_id = item["variant_id"]
            if variant_id:
                inventory_row = (
                    await self._session.execute(
                        text(
                            """
                            SELECT id, product_id, stock_quantity
                            FROM product_variants
                            WHERE id = :variant_id
                            FOR UPDATE
                            """
                        ),
                        {"variant_id": variant_id},
                    )
                ).mappings().first()
                if not inventory_row:
                    continue
                old_quantity = int(inventory_row["stock_quantity"] or 0)
                new_quantity = old_quantity + quantity
                await self._session.execute(
                    text("UPDATE product_variants SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
                    {"id": variant_id, "quantity": new_quantity},
                )
                await self._session.execute(
                    text(
                        """
                        INSERT INTO inventory_adjustment_logs (
                            id, product_id, variant_id, old_quantity, new_quantity, delta,
                            transaction_type, reference_code, reason, note
                        )
                        VALUES (
                            :id, :product_id, :variant_id, :old_quantity, :new_quantity, :delta,
                            'RETURN', :reference_code, 'ORDER_CANCELLED_RESTOCK', :note
                        )
                        """
                    ),
                    {
                        "id": uuid4(),
                        "product_id": inventory_row["product_id"],
                        "variant_id": variant_id,
                        "old_quantity": old_quantity,
                        "new_quantity": new_quantity,
                        "delta": quantity,
                        "reference_code": order.order_code,
                        "note": f"Restock after cancelling order for {item['product_name']}.",
                    },
                )
                continue

            if not item["product_id"]:
                continue
            inventory_row = (
                await self._session.execute(
                    text(
                        """
                        SELECT id, stock_quantity
                        FROM products
                        WHERE id = :product_id
                        FOR UPDATE
                        """
                    ),
                    {"product_id": item["product_id"]},
                )
            ).mappings().first()
            if not inventory_row:
                continue
            old_quantity = int(inventory_row["stock_quantity"] or 0)
            new_quantity = old_quantity + quantity
            await self._session.execute(
                text("UPDATE products SET stock_quantity = :quantity, updated_at = NOW() WHERE id = :id"),
                {"id": item["product_id"], "quantity": new_quantity},
            )
            await self._session.execute(
                text(
                    """
                    INSERT INTO inventory_adjustment_logs (
                        id, product_id, variant_id, old_quantity, new_quantity, delta,
                        transaction_type, reference_code, reason, note
                    )
                    VALUES (
                        :id, :product_id, NULL, :old_quantity, :new_quantity, :delta,
                        'RETURN', :reference_code, 'ORDER_CANCELLED_RESTOCK', :note
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "product_id": item["product_id"],
                    "old_quantity": old_quantity,
                    "new_quantity": new_quantity,
                    "delta": quantity,
                    "reference_code": order.order_code,
                    "note": f"Restock after cancelling order for {item['product_name']}.",
                },
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
        total_orders = await self._session.scalar(select(func.count(Order.id)))
        completed_orders = await self._session.scalar(
            select(func.count(Order.id)).where(Order.status == "COMPLETED")
        )
        total_revenue = await self._session.scalar(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.status == "COMPLETED")
        )
        ai_interactions = await self._session.scalar(select(func.count(AIContextLog.id)))
        loyalty_points_used = await self._session.scalar(
            select(func.coalesce(func.sum(Order.loyalty_points_used), 0))
        )
        return RevenueReportResponse(
            total_orders=total_orders or 0,
            completed_orders=completed_orders or 0,
            total_revenue=total_revenue or Decimal("0"),
            ai_interactions=ai_interactions or 0,
            loyalty_points_used=loyalty_points_used or 0,
        )


class ShippingQuoteUseCase:
    def __init__(self) -> None:
        self._shipping_pricing = SandboxShippingPricingService()

    def execute(self, *, shipping_address: str, subtotal_amount: Decimal, item_count: int) -> ShippingQuoteResponse:
        quote = self._shipping_pricing.quote(
            shipping_address=shipping_address,
            subtotal_amount=subtotal_amount,
            item_count=item_count,
        )
        return ShippingQuoteResponse(
            shipping_fee=quote.fee,
            zone=quote.zone,
            estimated_days=quote.estimated_days,
            free_shipping_applied=quote.free_shipping_applied,
            note=quote.note,
        )
