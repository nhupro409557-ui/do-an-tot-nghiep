from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class UsedDeviceIntakePayload(BaseModel):
    sourceType: Literal["USER_BUYBACK", "RETURNED_USED"]
    sellerUserId: UUID | None = None
    sellerName: str | None = Field(default=None, max_length=255)
    sellerPhone: str | None = Field(default=None, max_length=30)
    originalOrderId: UUID | None = None
    returnRequestId: UUID | None = None
    productId: UUID
    variantId: UUID | None = None
    imei: str = Field(min_length=15, max_length=80)
    serialNumber: str | None = Field(default=None, max_length=120)
    expectedPrice: Decimal | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("imei")
    @classmethod
    def validate_imei(cls, value: str) -> str:
        normalized = "".join(character for character in value if character.isdigit())
        if len(normalized) != 15:
            raise ValueError("IMEI phải gồm đúng 15 chữ số.")
        return normalized


class UsedDeviceStatusPayload(BaseModel):
    status: Literal[
        "RECEIVED",
        "INSPECTING",
        "ACCEPTED",
        "REJECTED",
        "CANCELLED",
    ]
    note: str | None = Field(default=None, max_length=2000)


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
