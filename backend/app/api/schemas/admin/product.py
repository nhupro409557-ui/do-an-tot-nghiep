from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class ProductBulkActionPayload(BaseModel):
    ids: list[UUID] | None = Field(default=None, min_length=1, max_length=500)
    productIds: list[UUID] | None = Field(default=None, min_length=1, max_length=500)
    action: str = Field(default="APPROVE", pattern="^(APPROVE|ARCHIVE|HIDE|RESTORE|DELETE)$")

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
    price: float = Field(gt=0)
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
    price: float = Field(gt=0)
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

    @model_validator(mode="after")
    def validate_price_relation(self) -> "ProductPayload":
        if self.discountPrice and self.discountPrice >= self.price:
            raise ValueError("Giá khuyến mãi phải nhỏ hơn giá niêm yết.")

        for variant in self.variants:
            regular = variant.compareAtPrice or variant.price
            if variant.salePrice and variant.salePrice >= regular:
                raise ValueError(f"Giá khuyến mãi của biến thể {variant.sku or ''} phải nhỏ hơn giá niêm yết.")

        # Validate duplicate SKUs in payload
        skus = [v.sku.strip() for v in self.variants if v.sku and isinstance(v.sku, str)]
        if len(skus) != len(set(skus)):
            seen = set()
            duplicates = []
            for sku in skus:
                if sku in seen:
                    duplicates.append(sku)
                else:
                    seen.add(sku)
            raise ValueError(f"Mã SKU của các biến thể không được trùng lặp trong yêu cầu: {', '.join(duplicates)}.")
        return self
