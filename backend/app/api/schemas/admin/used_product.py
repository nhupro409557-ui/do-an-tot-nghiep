from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator


class UsedDeviceIntakePayload(BaseModel):
    sourceType: Literal["USER_BUYBACK", "RETURNED_USED"]
    sellerUserId: UUID | None = None
    sellerName: str | None = Field(default=None, max_length=255)
    sellerPhone: str | None = Field(default=None, max_length=30)
    originalOrderId: UUID | None = None
    returnRequestId: UUID | None = None
    productId: UUID | None = None
    variantId: UUID | None = None
    externalProductName: str | None = Field(default=None, min_length=2, max_length=255)
    imei: str = Field(min_length=15, max_length=80)
    serialNumber: str | None = Field(default=None, max_length=120)
    sellerAddress: str | None = Field(default=None, max_length=500)
    sellerIdentityNumber: str | None = Field(default=None, max_length=30)
    expectedPrice: Decimal | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("imei")
    @classmethod
    def validate_imei(cls, value: str) -> str:
        normalized = "".join(character for character in value if character.isdigit())
        if len(normalized) != 15:
            raise ValueError("IMEI phải gồm đúng 15 chữ số.")
        return normalized

    @model_validator(mode="after")
    def validate_product_source(self):
        if self.productId is None and not (self.externalProductName or "").strip():
            raise ValueError("Phải chọn sản phẩm gốc hoặc nhập tên model ngoài danh mục.")
        if self.productId is not None and (self.externalProductName or "").strip():
            raise ValueError("Chỉ được chọn sản phẩm catalog hoặc nhập model ngoài danh mục, không dùng đồng thời.")
        if self.productId is None and self.variantId is not None:
            raise ValueError("Model ngoài danh mục không được gắn biến thể catalog.")
        return self


class UsedDeviceStatusPayload(BaseModel):
    status: Literal[
        "RECEIVED",
        "INSPECTING",
        "ACCEPTED",
        "REJECTED",
        "CANCELLED",
    ]
    note: str | None = Field(default=None, max_length=2000)
    sellerAddress: str | None = Field(default=None, max_length=500)
    sellerIdentityNumber: str | None = Field(default=None, max_length=30)
    ownershipConfirmed: bool = False
    acquisitionPaymentMethod: Literal["CASH", "BANK_TRANSFER", "TRADE_IN_CREDIT"] | None = None
    acquisitionPaymentReference: str | None = Field(default=None, max_length=120)


class UsedDeviceRepairPayload(BaseModel):
    description: str = Field(min_length=3, max_length=1000)
    cost: Decimal = Field(ge=0)
    repairedAt: date | None = None


class UsedDeviceInspectionPayload(BaseModel):
    outcome: Literal["APPRAISED", "REPAIR_REQUIRED", "REJECTED"]
    conditionGrade: Literal["A", "B", "C"] | None = None
    conditionScore: int | None = Field(default=None, ge=0, le=100)
    batteryHealth: int | None = Field(default=None, ge=0, le=100)
    checklist: dict[str, bool | str | int | float | None] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=30)
    repairCostEstimate: Decimal = Field(default=Decimal("0"), ge=0)
    proposedAcquisitionPrice: Decimal | None = Field(default=None, ge=0)
    proposedSalePrice: Decimal | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=4000)

    @field_validator("conditionGrade", "conditionScore")
    @classmethod
    def require_condition_for_appraisal(cls, value):
        return value


class UsedDeviceListingPayload(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    description: str = Field(min_length=20, max_length=10000)
    highlights: list[str] = Field(default_factory=list, max_length=12)
    images: list[str] = Field(min_length=1, max_length=20)
    warrantyMonths: int = Field(default=0, ge=0, le=36)
    manufacturerWarrantyEnabled: bool = False
    manufacturerWarrantyProvider: str | None = Field(default=None, max_length=120)
    manufacturerWarrantyActivatedAt: date | None = None
    manufacturerWarrantyTotalMonths: int | None = Field(default=None, ge=1, le=60)
    priceComparisonNote: str | None = Field(default=None, max_length=1000)

    @field_validator("highlights")
    @classmethod
    def normalize_highlights(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    @field_validator("images")
    @classmethod
    def normalize_images(cls, value: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if not normalized:
            raise ValueError("Bài đăng phải có ít nhất một ảnh thực tế.")
        return normalized


class UsedDeviceLifecyclePayload(BaseModel):
    status: Literal["READY_FOR_PRICING", "RETURNED_QC", "REPAIRING", "RETIRED"]
    note: str | None = Field(default=None, max_length=2000)


class UsedDeviceListingStatusPayload(BaseModel):
    status: Literal["DRAFT", "PENDING_APPROVAL", "PUBLISHED", "HIDDEN"]
    note: str | None = Field(default=None, max_length=2000)


class UsedDevicePricePayload(BaseModel):
    salePrice: Decimal = Field(gt=0)
    reason: str = Field(min_length=5, max_length=1000)
