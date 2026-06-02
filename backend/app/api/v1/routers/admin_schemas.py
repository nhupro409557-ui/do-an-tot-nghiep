from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CategoryPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=80)
    slug: str | None = Field(default=None, max_length=120)
    icon: str | None = Field(default=None, max_length=80)
    iconUrl: str | None = None
    bannerUrl: str | None = None
    parentId: UUID | None = None
    order: int = Field(default=0, ge=0)
    isActive: bool = True
    status: str = Field(default="ACTIVE", pattern="^(DRAFT|PENDING_REVIEW|APPROVED|ACTIVE|INACTIVE|REJECTED)$")
    seoTitle: str | None = Field(default=None, max_length=255)
    seoDescription: str | None = None
    seoKeywords: str | None = None
    specFields: list[dict] = Field(default_factory=list)
    filterConfig: list[dict] = Field(default_factory=list)
    inventoryPolicy: dict = Field(default_factory=dict)
    warrantyPolicy: dict = Field(default_factory=dict)
    allowSpecTypeMigration: bool = False
    version: int | None = Field(default=None, ge=1)


class CategorySlugCheckPayload(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    excludeId: UUID | None = None


class CategoryReorderItem(BaseModel):
    id: UUID
    order: int = Field(ge=0)
    parentId: UUID | None = None


class CategoryReorderPayload(BaseModel):
    items: list[CategoryReorderItem] = Field(min_length=1)


class CategoryBulkPayload(BaseModel):
    items: list[CategoryReorderItem] | None = Field(default=None, min_length=1)
    status: str | None = Field(default=None, pattern="^(DRAFT|ACTIVE|INACTIVE)$")
    ids: list[UUID] | None = Field(default=None, min_length=1, max_length=200)


class BrandPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=80)
    slug: str | None = Field(default=None, max_length=120)
    order: int = Field(default=0, ge=0)
    isActive: bool = True
    categoryIds: list[UUID] = Field(default_factory=list)
    logoUrl: str | None = None
    logoAltText: str | None = Field(default=None, max_length=255)
    landingTitle: str | None = Field(default=None, max_length=255)
    seoTitle: str | None = Field(default=None, max_length=255)
    seoDescription: str | None = None


class BrandCodeCheckPayload(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    excludeId: UUID | None = None


class BrandImportItem(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=80)
    logoUrl: str | None = None
    order: int = Field(default=0, ge=0)


class BrandImportPayload(BaseModel):
    items: list[BrandImportItem] = Field(min_length=1, max_length=500)
    mode: str = Field(default="skip", pattern="^(skip|upsert)$")
    sourceFilename: str | None = Field(default=None, max_length=255)


class BrandStatusPayload(BaseModel):
    isActive: bool


class BrandBulkStatusPayload(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=200)
    isActive: bool


class ProductBulkActionPayload(BaseModel):
    ids: list[UUID] | None = Field(default=None, min_length=1, max_length=500)
    productIds: list[UUID] | None = Field(default=None, min_length=1, max_length=500)
    action: str = Field(default="APPROVE", pattern="^(APPROVE|ARCHIVE|DELETE)$")
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CategoryPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=80)
    slug: str | None = Field(default=None, max_length=120)
    icon: str | None = Field(default=None, max_length=80)
    iconUrl: str | None = None
    bannerUrl: str | None = None
    parentId: UUID | None = None
    order: int = Field(default=0, ge=0)
    isActive: bool = True
    status: str = Field(default="ACTIVE", pattern="^(DRAFT|PENDING_REVIEW|APPROVED|ACTIVE|INACTIVE|REJECTED)$")
    seoTitle: str | None = Field(default=None, max_length=255)
    seoDescription: str | None = None
    seoKeywords: str | None = None
    specFields: list[dict] = Field(default_factory=list)
    filterConfig: list[dict] = Field(default_factory=list)
    inventoryPolicy: dict = Field(default_factory=dict)
    warrantyPolicy: dict = Field(default_factory=dict)
    allowSpecTypeMigration: bool = False
    version: int | None = Field(default=None, ge=1)


class CategorySlugCheckPayload(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    excludeId: UUID | None = None


class CategoryReorderItem(BaseModel):
    id: UUID
    order: int = Field(ge=0)
    parentId: UUID | None = None


class CategoryReorderPayload(BaseModel):
    items: list[CategoryReorderItem] = Field(min_length=1)


class CategoryBulkPayload(BaseModel):
    items: list[CategoryReorderItem] | None = Field(default=None, min_length=1)
    status: str | None = Field(default=None, pattern="^(DRAFT|ACTIVE|INACTIVE)$")
    ids: list[UUID] | None = Field(default=None, min_length=1, max_length=200)


class BrandPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=80)
    slug: str | None = Field(default=None, max_length=120)
    order: int = Field(default=0, ge=0)
    isActive: bool = True
    categoryIds: list[UUID] = Field(default_factory=list)
    logoUrl: str | None = None
    logoAltText: str | None = Field(default=None, max_length=255)
    landingTitle: str | None = Field(default=None, max_length=255)
    seoTitle: str | None = Field(default=None, max_length=255)
    seoDescription: str | None = None


class BrandCodeCheckPayload(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    excludeId: UUID | None = None


class BrandImportItem(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=80)
    logoUrl: str | None = None
    order: int = Field(default=0, ge=0)


class BrandImportPayload(BaseModel):
    items: list[BrandImportItem] = Field(min_length=1, max_length=500)
    mode: str = Field(default="skip", pattern="^(skip|upsert)$")
    sourceFilename: str | None = Field(default=None, max_length=255)


class BrandStatusPayload(BaseModel):
    isActive: bool


class BrandBulkStatusPayload(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=200)
    isActive: bool


class ProductBulkActionPayload(BaseModel):
    ids: list[UUID] | None = Field(default=None, min_length=1, max_length=500)
    productIds: list[UUID] | None = Field(default=None, min_length=1, max_length=500)
    action: str = Field(default="APPROVE", pattern="^(APPROVE|ARCHIVE|DELETE)$")


class ProductImportPayload(BaseModel):
    sourceFilename: str


class ProductVariantPayload(BaseModel):
    id: UUID | None = None
    sku: str | None = Field(default=None, max_length=120)
    colorName: str | None = Field(default=None, max_length=100)
    colorCode: str | None = Field(default=None, max_length=30)
    storage: str | None = Field(default=None, max_length=80)
    ram: str | None = Field(default=None, max_length=80)
    configuration: str | None = Field(default=None, max_length=160)
    specs: dict = Field(default_factory=dict)
    imageUrl: str | None = None
    images: list[str] = Field(default_factory=list)
    price: float = Field(ge=0)
    salePrice: float | None = Field(default=None, ge=0)
    stockQuantity: int = Field(default=0, ge=0)
    isActive: bool = True
    isDefault: bool = False
    compareAtPrice: float | None = Field(default=None, ge=0)
    status: str = Field(default="active", max_length=50)
    attributes: dict = Field(default_factory=dict)


class ProductAccessoryOfferPayload(BaseModel):
    productId: UUID
    discountType: str = Field(default="PERCENT", pattern="^(FIXED|PERCENT)$")
    discountValue: float = Field(ge=0)
    maxQuantity: int = Field(default=1, ge=1, le=999)


class ProductAttachedServicePayload(BaseModel):
    serviceId: UUID


class AttachedServicePayload(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=180)
    serviceType: str = Field(default="SUPPORT_SERVICE", pattern="^(PRODUCT_SERVICE|SUPPORT_SERVICE)$")
    attributeGroup: str | None = Field(default=None, max_length=80)
    durationMonths: int = Field(default=0, ge=0, le=120)
    priceMode: str = Field(default="FIXED", pattern="^(FIXED|PERCENT|TIERED_AMOUNT)$")
    fixedPrice: float = Field(default=0, ge=0)
    percentValue: float = Field(default=0, ge=0)
    baseAmount: float = Field(default=0, ge=0)
    isActive: bool = True
    metadata: dict = Field(default_factory=dict)


class ProductPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: float = Field(ge=0)
    discountPrice: float | None = Field(default=None, ge=0)
    stock: int = Field(default=0, ge=0)
    brand: str = Field(default="Khac", max_length=100)
    category: str = Field(default="ACCESSORY", max_length=50)
    categoryId: UUID | None = None
    subcategoryId: UUID | None = None
    brandId: UUID | None = None
    imageUrl: str | None = None
    images: list[str] = Field(default_factory=list)
    mediaMetadata: dict = Field(default_factory=dict)
    videoUrl: str | None = None
    description: str | None = None
    specifications: dict = Field(default_factory=dict)
    variants: list[ProductVariantPayload] = Field(default_factory=list)
    isFeatured: bool = False
    isFlashSale: bool = False
    status: str = Field(default="DRAFT", max_length=30)
    updatedAt: str | None = None
    version: int | None = Field(default=None, ge=1)
    options: list[dict] = Field(default_factory=list)


class InventoryAdjustmentPayload(BaseModel):
    variantId: UUID | None = None
    delta: int | None = None
    quantity: int | None = Field(default=None, ge=0)
    transactionType: str = Field(default="ADJUSTMENT", pattern="^(RECEIPT|ADJUSTMENT|SALE|RETURN|REVERSAL)$")
    referenceCode: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=500)
    supplierName: str | None = Field(default=None, max_length=160)
    unitCost: float | None = Field(default=None, ge=0)
    locationCode: str | None = Field(default=None, max_length=60)
    locationName: str | None = Field(default=None, max_length=160)
    imeis: list[str] = Field(default_factory=list, max_length=500)


class InventorySettingsPayload(BaseModel):
    minimumStock: int = Field(default=0, ge=0)
    blockSaleWhenOutOfStock: bool = True
    preferredLocationCode: str | None = Field(default=None, max_length=60)
    preferredLocationName: str | None = Field(default=None, max_length=160)
    cycleCountDays: int | None = Field(default=None, ge=1, le=365)


class VariantInventoryPayload(BaseModel):
    quantity: int = Field(ge=0)
    referenceCode: str = Field(min_length=1, max_length=120)
    transactionType: str = Field(default="ADJUSTMENT", pattern="^(RECEIPT|ADJUSTMENT|SALE|RETURN|REVERSAL)$")
    reason: str = Field(default="MANUAL_SET", max_length=80)
    note: str | None = Field(default=None, max_length=500)


class VoucherPayload(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    discountType: str = Field(default="FIXED", max_length=20)
    discountAmount: float = Field(gt=0)
    minOrderValue: float = Field(default=0, ge=0)
    maxDiscount: float | None = Field(default=None, ge=0)
    usageLimit: int = Field(default=0, ge=0)
    totalBudgetCap: float | None = Field(default=None, ge=0)
    perUserLimit: int = Field(default=0, ge=0)
    perDeviceLimit: int = Field(default=0, ge=0)
    perIpLimit: int = Field(default=0, ge=0)
    campaignType: str = Field(default="CONVERSION", max_length=40)
    audienceType: str = Field(default="PUBLIC", max_length=40)
    eligibleTiers: list[str] = Field(default_factory=list)
    eligibleUserRegisteredAfter: str | None = None
    assignedUserId: UUID | None = None
    includeProductIds: list[str] = Field(default_factory=list)
    excludeProductIds: list[str] = Field(default_factory=list)
    includeCategoryIds: list[str] = Field(default_factory=list)
    excludeCategoryIds: list[str] = Field(default_factory=list)
    firstOrderOnly: bool = False
    hiddenCode: bool = False
    abandonedCartOnly: bool = False
    validityDaysAfterClaim: int = Field(default=0, ge=0)
    stackable: bool = False
    refundPolicy: str = Field(default="SHOP_FAULT_ONLY", max_length=40)
    startsAt: str | None = None
    endsAt: str | None = None
    internalNote: str | None = None
    status: str = Field(default="ACTIVE", max_length=30)


class ContentCommentPayload(BaseModel):
    id: str | None = Field(default=None, max_length=80)
    userName: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=1000)
    parentId: str | None = Field(default=None, max_length=80)
    isHidden: bool = False


class ContentPayload(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    contentType: str = Field(default="VIDEO", max_length=30)
    videoSource: str = Field(default="UPLOAD", max_length=30)
    videoCategory: str = Field(default="PRODUCT", max_length=60)
    status: str = Field(default="DRAFT", max_length=30)
    videoUrl: str | None = None
    thumbnailUrl: str | None = None
    bannerImageUrl: str | None = None
    contentBody: str = ""
    ctaLabel: str | None = Field(default=None, max_length=160)
    ctaUrl: str | None = None
    productIds: list[str] = Field(default_factory=list)
    categoryIds: list[str] = Field(default_factory=list)
    comments: list[ContentCommentPayload] = Field(default_factory=list)
    likeCount: int = Field(default=0, ge=0)
    viewCount: int = Field(default=0, ge=0)
    sortOrder: int = Field(default=0, ge=0)
    scheduledAt: str | None = None
    publishedAt: str | None = None
    isActive: bool = True
    version: int | None = Field(default=None, ge=1)


class AdminVideoCommentReplyPayload(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class AdminVideoCommentVisibilityPayload(BaseModel):
    isHidden: bool = True


class ReviewStatusPayload(BaseModel):
    status: str | None = Field(default=None, pattern="^(PENDING|PUBLISHED|HIDDEN|REJECTED)$")
    moderationNote: str | None = Field(default=None, max_length=1000)
    shopReply: str | None = Field(default=None, max_length=2000)
    flaggedReason: str | None = Field(default=None, max_length=1000)
    isSpam: bool | None = None
    spamReason: str | None = Field(default=None, max_length=1000)


class UserRolePayload(BaseModel):
    role: str = Field(pattern="^(CUSTOMER|STAFF_ADMIN)$")
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|SUSPENDED)$")
    permissionCodes: list[str] | None = None


class RolePermissionsPayload(BaseModel):
    permissionCodes: list[str] = Field(default_factory=list)


class StaffCreatePayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    fullName: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|SUSPENDED)$")
    permissionCodes: list[str] = Field(default_factory=list)


class UserPermissionsPayload(BaseModel):
    permissionCodes: list[str] = Field(default_factory=list)


class CustomerTagsPayload(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=20)


class CustomerBulkTagsPayload(BaseModel):
    userIds: list[UUID] = Field(min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=20)


class CustomerNotePayload(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CustomerLoyaltyAdjustmentPayload(BaseModel):
    delta: int = Field(ge=-500000, le=500000)
    reason: str = Field(min_length=3, max_length=255)


class CustomerVoucherIssuePayload(BaseModel):
    voucherId: UUID
    note: str | None = Field(default=None, max_length=255)


class CustomerBulkStatusPayload(BaseModel):
    userIds: list[UUID] = Field(min_length=1, max_length=200)
    status: str = Field(pattern="^(ACTIVE|SUSPENDED)$")


