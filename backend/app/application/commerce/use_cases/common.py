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
    "PENDING": "Chờ xử lý",
    "CONFIRMED": "Đã xác nhận",
    "PAID": "Đã thanh toán",
    "PROCESSING": "Đang đóng gói",
    "SHIPPED": "Đang giao hàng",
    "COMPLETED": "Đã giao hàng thành công",
    "CANCELLED": "Đã hủy",
    "REFUNDED": "Đã hoàn tiền",
    "PAYMENT_FAILED": "Thanh toán thất bại",
    "RETURNING": "Đang hoàn hàng",
    "RETURNED": "Đã nhận lại hàng trả",
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
                "Voucher chưa đến thời gian áp dụng.",
                {"starts_at": voucher.starts_at.isoformat()},
            )
        if voucher.ends_at and voucher.ends_at < context.now:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_EXPIRED",
                "Voucher đã hết hạn.",
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
                "Vui lòng đăng nhập và lưu voucher vào ví trước khi áp dụng.",
            )
        claimed = await service._get_claimed_voucher(user_id=context.user_id, voucher_id=voucher.id)
        if claimed is None:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_CLAIM_REQUIRED",
                "Bạn cần lưu voucher này vào ví trước khi sử dụng.",
                {"claim_window_days": voucher.validity_days_after_claim},
            )
        if claimed.expires_at and claimed.expires_at < context.now:
            await service._expire_wallet_voucher(claimed)
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_WALLET_EXPIRED",
                "Voucher trong ví của bạn đã hết hạn.",
                {"expires_at": claimed.expires_at.isoformat()},
            )
        if claimed.status not in {"AVAILABLE", "RESERVED"}:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_WALLET_UNAVAILABLE",
                "Voucher này không còn khả dụng trong ví của bạn.",
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
            f"Giá trị đơn hàng cần đạt tối thiểu {minimum:,.0f} để dùng voucher này.",
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
                "Voucher không áp dụng cho kênh bán hàng này.",
                {"allowed_channels": sorted(allowed_channels), "current_channel": context.channel},
            )
        if allowed_payment_methods and context.payment_method and context.payment_method.upper() not in allowed_payment_methods:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_PAYMENT_METHOD",
                "Voucher không áp dụng cho phương thức thanh toán này.",
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
                "Voucher đã đạt giới hạn lượt sử dụng.",
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
                "Ngân sách chiến dịch voucher đã được dùng hết.",
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
                "Voucher này được dành cho khách hàng khác.",
            )
        if voucher.audience_type == "SPECIFIC_USER" and not voucher.assigned_user_id:
            if not context.user_id:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_ASSIGNED_USER_SIGN_IN",
                    "Vui lòng đăng nhập để sử dụng voucher được cấp riêng.",
                )
            if not await commerce_repo.has_user_voucher_assignment(
                service._session,
                user_id=context.user_id,
                voucher_id=voucher.id,
            ):
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_ASSIGNED_USER",
                    "Voucher này được dành cho khách hàng khác.",
                )
        if voucher.eligible_user_registered_after and context.user_id:
            registered_at = await commerce_repo.get_user_created_at(service._session, context.user_id)
            if registered_at and registered_at < voucher.eligible_user_registered_after:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_NEW_USER_ONLY",
                    "Voucher chỉ áp dụng cho tài khoản mới hơn.",
                    {"eligible_user_registered_after": voucher.eligible_user_registered_after.isoformat()},
                )
        eligible_tiers = voucher.eligible_tiers if isinstance(voucher.eligible_tiers, list) else []
        if eligible_tiers and (context.user_tier or "").upper() not in {str(tier).upper() for tier in eligible_tiers}:
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_TIER",
                "Voucher không áp dụng cho hạng thành viên của bạn.",
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
                "Vui lòng đăng nhập để sử dụng voucher cho đơn hàng đầu tiên.",
            )
        if await service._user_order_count(context.user_id) > 0:
            return service._invalid(
                context.voucher.code,
                "VOUCHER_ERR_FIRST_ORDER_ONLY",
                "Voucher chỉ áp dụng cho đơn hàng đầu tiên.",
            )
        return None


class AbandonedCartRule(VoucherRule):
    async def check(self, service: "VoucherService", context: VoucherValidationContext) -> VoucherValidationResponse | None:
        if context.voucher.abandoned_cart_only and not context.abandoned_cart_recovery:
            return service._invalid(
                context.voucher.code,
                "VOUCHER_ERR_ABANDONED_CART",
                "Voucher chỉ áp dụng cho ưu đãi khôi phục giỏ hàng bỏ quên.",
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
                    "Voucher đã đạt giới hạn sử dụng cho mỗi khách hàng.",
                    {"per_user_limit": voucher.per_user_limit, "used_count": usage},
                )
        if voucher.per_device_limit > 0 and context.device_id:
            usage = await service._voucher_usage_count_by("voucher_device_id", context.device_id, voucher.code)
            if usage >= voucher.per_device_limit:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_DEVICE_LIMIT",
                    "Voucher đã đạt giới hạn sử dụng theo thiết bị.",
                    {"per_device_limit": voucher.per_device_limit, "used_count": usage},
                )
        if voucher.per_ip_limit > 0 and context.ip_address:
            usage = await service._voucher_usage_count_by("voucher_ip_address", context.ip_address, voucher.code)
            if usage >= voucher.per_ip_limit:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_IP_LIMIT",
                    "Voucher đã đạt giới hạn sử dụng theo địa chỉ IP.",
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
                "Voucher không áp dụng cho sản phẩm trong đơn hàng này.",
                {"required_product_ids": sorted(include_products)},
            )
        if exclude_products:
            blocked = sorted(context.product_ids.intersection(exclude_products))
            if blocked:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_PRODUCT_EXCLUDED",
                    "Voucher loại trừ một hoặc nhiều sản phẩm trong đơn hàng này.",
                    {"blocked_product_ids": blocked},
                )
        if include_categories and not context.category_ids.intersection(include_categories):
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_CATEGORY_SCOPE",
                "Voucher không áp dụng cho danh mục trong đơn hàng này.",
                {"required_category_ids": sorted(include_categories)},
            )
        if exclude_categories:
            blocked = sorted(context.category_ids.intersection(exclude_categories))
            if blocked:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_CATEGORY_EXCLUDED",
                    "Voucher loại trừ một hoặc nhiều danh mục trong đơn hàng này.",
                    {"blocked_category_ids": blocked},
                )
        if include_brands and not context.brand_ids.intersection(include_brands):
            return service._invalid(
                voucher.code,
                "VOUCHER_ERR_BRAND_SCOPE",
                "Voucher không áp dụng cho thương hiệu trong đơn hàng này.",
                {"required_brand_ids": sorted(include_brands)},
            )
        if exclude_brands:
            blocked = sorted(context.brand_ids.intersection(exclude_brands))
            if blocked:
                return service._invalid(
                    voucher.code,
                    "VOUCHER_ERR_BRAND_EXCLUDED",
                    "Voucher loại trừ một hoặc nhiều thương hiệu trong đơn hàng này.",
                    {"blocked_brand_ids": blocked},
                )
        return None

__all__ = [name for name in globals() if not name.startswith("__")]
