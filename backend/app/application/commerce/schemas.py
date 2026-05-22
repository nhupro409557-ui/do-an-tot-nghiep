from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CheckoutItem(BaseModel):
    product_id: UUID | None = None
    variant_id: UUID | None = None
    product_name: str = Field(min_length=1, max_length=255)
    quantity: int = Field(gt=0, le=99)
    unit_price: Decimal = Field(ge=0)
    category_id: UUID | None = None


class ShippingInfo(BaseModel):
    recipient_name: str = Field(min_length=2, max_length=255)
    recipient_phone: str = Field(min_length=8, max_length=30)
    shipping_address: str = Field(min_length=10, max_length=1000)


class ShippingQuoteRequest(BaseModel):
    shipping_address: str = Field(min_length=10, max_length=1000)
    subtotal_amount: Decimal = Field(ge=0)
    item_count: int = Field(gt=0, le=99)


class ShippingQuoteResponse(BaseModel):
    shipping_fee: Decimal = Field(ge=0)
    zone: str
    estimated_days: int = Field(ge=1)
    free_shipping_applied: bool = False
    note: str = ""


class VoucherValidationRequest(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    subtotal_amount: Decimal = Field(ge=0)
    user_id: UUID | None = None
    user_tier: str | None = None
    abandoned_cart_recovery: bool = False
    device_id: str | None = Field(default=None, max_length=120)
    ip_address: str | None = Field(default=None, max_length=80)
    product_ids: list[str] = Field(default_factory=list, max_length=99)
    category_ids: list[str] = Field(default_factory=list, max_length=99)


class VoucherValidationResponse(BaseModel):
    code: str
    valid: bool
    discount_amount: Decimal = Field(ge=0)
    message: str
    error_code: str | None = None
    metadata: dict = Field(default_factory=dict)


class ClaimVoucherRequest(BaseModel):
    user_id: UUID


class UserVoucherResponse(BaseModel):
    id: str
    voucher_id: str
    user_id: str
    code: str
    status: str
    claimed_at: str | None = None
    expires_at: str | None = None
    used_at: str | None = None
    order_id: str | None = None
    discount_type: str
    discount_amount: Decimal = Field(ge=0)
    min_order_value: Decimal = Field(ge=0)
    max_discount: Decimal | None = Field(default=None, ge=0)


class CreateOrderRequest(BaseModel):
    user_id: UUID | None = None
    items: list[CheckoutItem] = Field(min_length=1, max_length=99)
    shipping: ShippingInfo
    payment_method: str = Field(pattern="^(VNPAY|MOMO|CREDIT_CARD|COD)$")
    voucher_code: str | None = Field(default=None, max_length=50)
    voucher_device_id: str | None = Field(default=None, max_length=120)
    voucher_ip_address: str | None = Field(default=None, max_length=80)
    loyalty_points_used: int = Field(default=0, ge=0)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)


class CreateOrderResponse(BaseModel):
    order_id: UUID
    order_code: str
    payment_method: str
    payment_status: str
    shipping_fee: Decimal
    total_amount: Decimal
    loyalty_points_earned: int
    checkout_url: str | None = None


class UpdateOrderStatusRequest(BaseModel):
    status: str = Field(pattern="^(PENDING|CONFIRMED|PAID|PROCESSING|SHIPPED|COMPLETED|CANCELLED|REFUNDED|PAYMENT_FAILED|RETURNING|RETURNED)$")


class AdminUpdateOrderRequest(BaseModel):
    status: str | None = Field(default=None, pattern="^(PENDING|CONFIRMED|PAID|PROCESSING|SHIPPED|COMPLETED|CANCELLED|REFUNDED|PAYMENT_FAILED|RETURNING|RETURNED)$")
    assigned_staff_name: str | None = Field(default=None, max_length=255)
    internal_note: str | None = Field(default=None, max_length=4000)
    cancellation_reason: str | None = Field(default=None, max_length=1000)
    shipping_provider: str | None = Field(default=None, max_length=120)
    tracking_code: str | None = Field(default=None, max_length=120)
    refund_payment: bool = False
    changed_by: str | None = Field(default=None, max_length=255)


class RevenueReportResponse(BaseModel):
    total_orders: int
    completed_orders: int
    total_revenue: Decimal
    ai_interactions: int
    loyalty_points_used: int
