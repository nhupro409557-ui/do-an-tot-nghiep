from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


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
