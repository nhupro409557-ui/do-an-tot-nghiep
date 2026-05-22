from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, Table, Column, Text
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    role_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("roles.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    marketing_opt_in: Mapped[bool] = mapped_column(default=False, nullable=False)
    profile_json: Mapped[dict] = mapped_column("profile", JSONB, default=dict, nullable=False)
    addresses: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    loyalty_points_balance: Mapped[int] = mapped_column(default=0, nullable=False)
    loyalty_tier: Mapped[str] = mapped_column(String(30), default="MEMBER", nullable=False)
    loyalty_wallet_status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now, onupdate=utc_now)


brand_categories = Table(
    "brand_categories",
    Base.metadata,
    Column("brand_id", PG_UUID(as_uuid=True), ForeignKey("brands.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", PG_UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    parent_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("categories.id"))
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(80))
    icon_url: Mapped[str | None] = mapped_column(Text)
    banner_url: Mapped[str | None] = mapped_column(Text)
    spec_fields: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    filter_config: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    hidden_by_parent: Mapped[bool] = mapped_column(default=False, nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    workflow_status: Mapped[str] = mapped_column(String(30), default="APPROVED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now, onupdate=utc_now)


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    slug: Mapped[str | None] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text)
    logo_alt_text: Mapped[str | None] = mapped_column(String(255))
    landing_title: Mapped[str | None] = mapped_column(String(255))
    seo_title: Mapped[str | None] = mapped_column(String(255))
    seo_description: Mapped[str | None] = mapped_column(Text)
    cache_version: Mapped[int] = mapped_column(default=1, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now, onupdate=utc_now)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    category_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("categories.id"))
    subcategory_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("categories.id"))
    brand_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("brands.id"))
    description: Mapped[str | None] = mapped_column(Text)
    specifications: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    price: Mapped[float] = mapped_column(NUMERIC(14, 2), nullable=False)
    sale_price: Mapped[float | None] = mapped_column(NUMERIC(14, 2))
    stock_quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(Text)
    images: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    colors: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    capacities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    promotions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    badge: Mapped[str | None] = mapped_column(String(80))
    rating: Mapped[float | None] = mapped_column(NUMERIC(3, 2))
    review_count: Mapped[int] = mapped_column(default=0, nullable=False)
    is_featured: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_flash_sale: Mapped[bool] = mapped_column(default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now, onupdate=utc_now)


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    sku: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    color_name: Mapped[str | None] = mapped_column(String(100))
    color_code: Mapped[str | None] = mapped_column(String(30))
    storage: Mapped[str | None] = mapped_column(String(80))
    ram: Mapped[str | None] = mapped_column(String(80))
    configuration: Mapped[str | None] = mapped_column(String(160))
    specs: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(NUMERIC(14, 2), nullable=False)
    sale_price: Mapped[float | None] = mapped_column(NUMERIC(14, 2))
    stock_quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("price >= 0"),
        CheckConstraint("sale_price IS NULL OR sale_price >= 0"),
        CheckConstraint("stock_quantity >= 0"),
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    order_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(30), default="UNPAID", nullable=False)
    subtotal_amount: Mapped[float] = mapped_column(NUMERIC(14, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, nullable=False)
    shipping_fee: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(NUMERIC(14, 2), nullable=False)
    loyalty_points_earned: Mapped[int] = mapped_column(default=0, nullable=False)
    loyalty_points_used: Mapped[int] = mapped_column(default=0, nullable=False)
    voucher_code: Mapped[str | None] = mapped_column(String(50))
    voucher_claim_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("user_vouchers.id"))
    voucher_device_id: Mapped[str | None] = mapped_column(String(120))
    voucher_ip_address: Mapped[str | None] = mapped_column(String(80))
    idempotency_key: Mapped[str | None] = mapped_column(String(120))
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_staff_name: Mapped[str | None] = mapped_column(String(255))
    internal_note: Mapped[str | None] = mapped_column(Text)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    shipping_provider: Mapped[str | None] = mapped_column(String(120))
    tracking_code: Mapped[str | None] = mapped_column(String(120))
    shipped_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    refunded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now, onupdate=utc_now)


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    order_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id"))
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    points: Mapped[int] = mapped_column(nullable=False)
    balance_before: Mapped[int] = mapped_column(nullable=False)
    balance_after: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)

    __table_args__ = (
        CheckConstraint("points > 0"),
        CheckConstraint("balance_before >= 0"),
        CheckConstraint("balance_after >= 0"),
    )


class AIContextLog(Base):
    __tablename__ = "ai_context_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    conversation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    request_scope: Mapped[str] = mapped_column(String(50), default="SALES_ASSISTANT", nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_response: Mapped[str | None] = mapped_column(Text)
    refusal_reason: Mapped[str | None] = mapped_column(Text)
    dynamic_context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(30), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[float] = mapped_column(NUMERIC(14, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(NUMERIC(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)

    __table_args__ = (
        CheckConstraint("quantity > 0"),
        CheckConstraint("unit_price >= 0"),
        CheckConstraint("total_price >= 0"),
    )


class OrderHistoryLog(Base):
    __tablename__ = "order_history_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(40))
    new_status: Mapped[str] = mapped_column(String(40), nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)


class Voucher(Base):
    __tablename__ = "vouchers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[float] = mapped_column(NUMERIC(14, 2), nullable=False)
    min_order_value: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, nullable=False)
    max_discount: Mapped[float | None] = mapped_column(NUMERIC(14, 2))
    usage_limit: Mapped[int] = mapped_column(default=0, nullable=False)
    used_count: Mapped[int] = mapped_column(default=0, nullable=False)
    total_budget_cap: Mapped[float | None] = mapped_column(NUMERIC(14, 2))
    total_discount_used: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, nullable=False)
    per_user_limit: Mapped[int] = mapped_column(default=0, nullable=False)
    per_device_limit: Mapped[int] = mapped_column(default=0, nullable=False)
    per_ip_limit: Mapped[int] = mapped_column(default=0, nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(40), default="CONVERSION", nullable=False)
    audience_type: Mapped[str] = mapped_column(String(40), default="PUBLIC", nullable=False)
    eligible_tiers: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    eligible_user_registered_after: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    assigned_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    include_product_ids: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    exclude_product_ids: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    include_category_ids: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    exclude_category_ids: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    first_order_only: Mapped[bool] = mapped_column(default=False, nullable=False)
    hidden_code: Mapped[bool] = mapped_column(default=False, nullable=False)
    abandoned_cart_only: Mapped[bool] = mapped_column(default=False, nullable=False)
    validity_days_after_claim: Mapped[int] = mapped_column(default=0, nullable=False)
    stackable: Mapped[bool] = mapped_column(default=False, nullable=False)
    refund_policy: Mapped[str] = mapped_column(String(40), default="SHOP_FAULT_ONLY", nullable=False)
    internal_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("discount_type IN ('FIXED', 'PERCENT')"),
        CheckConstraint("discount_value > 0"),
        CheckConstraint("min_order_value >= 0"),
        CheckConstraint("max_discount IS NULL OR max_discount >= 0"),
        CheckConstraint("usage_limit >= 0"),
        CheckConstraint("used_count >= 0"),
        CheckConstraint("total_budget_cap IS NULL OR total_budget_cap >= 0"),
        CheckConstraint("total_discount_used >= 0"),
        CheckConstraint("per_user_limit >= 0"),
        CheckConstraint("per_device_limit >= 0"),
        CheckConstraint("per_ip_limit >= 0"),
        CheckConstraint("validity_days_after_claim >= 0"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'EXPIRED')"),
    )


class UserVoucher(Base):
    __tablename__ = "user_vouchers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    voucher_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("vouchers.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="AVAILABLE", nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    order_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("status IN ('AVAILABLE', 'RESERVED', 'USED', 'EXPIRED', 'REVOKED')"),
    )


class ProductReview(Base):
    __tablename__ = "product_reviews"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    order_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id"))
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    user_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    media_urls: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    moderation_note: Mapped[str | None] = mapped_column(Text)
    shop_reply: Mapped[str | None] = mapped_column(Text)
    shop_replied_by: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    shop_replied_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    flagged_reason: Mapped[str | None] = mapped_column(Text)
    flagged_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    is_spam: Mapped[bool] = mapped_column(default=False, nullable=False)
    spam_reason: Mapped[str | None] = mapped_column(Text)
    review_window_expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    edited_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5"),
        CheckConstraint("status IN ('PENDING', 'PUBLISHED', 'HIDDEN', 'REJECTED')"),
    )


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[float] = mapped_column(NUMERIC(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    transaction_ref: Mapped[str | None] = mapped_column(String(120))
    checkout_url: Mapped[str | None] = mapped_column(Text)
    raw_response: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=utc_now, onupdate=utc_now)

    __table_args__ = (
        CheckConstraint("provider IN ('VNPAY', 'MOMO', 'CREDIT_CARD', 'COD')"),
        CheckConstraint("amount >= 0"),
        CheckConstraint("status IN ('PENDING', 'PAID', 'FAILED', 'REFUNDED')"),
    )
