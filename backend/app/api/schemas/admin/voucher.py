from datetime import datetime
from uuid import UUID
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


class VoucherPayload(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    discountType: Literal['FIXED', 'PERCENT'] = 'FIXED'
    discountAmount: float = Field(gt=0)
    minOrderValue: float = Field(default=0, ge=0)
    maxDiscount: Optional[float] = Field(default=None, ge=0)
    usageLimit: int = Field(default=0, ge=0)
    totalBudgetCap: Optional[float] = Field(default=None, ge=0)
    perUserLimit: int = Field(default=0, ge=0)
    perDeviceLimit: int = Field(default=0, ge=0)
    perIpLimit: int = Field(default=0, ge=0)
    redemptionPoints: int = Field(default=0, ge=0)
    campaignType: Literal['CONVERSION', 'ACQUISITION', 'RETENTION', 'CUSTOMER_SERVICE', 'LOYALTY', 'FLASH_SALE', 'ABANDONED_CART'] = 'CONVERSION'
    audienceType: Literal['PUBLIC', 'NEW_CUSTOMER', 'MEMBER_TIER', 'SPECIFIC_USER', 'HIDDEN', 'ABANDONED_CART'] = 'PUBLIC'
    displayTitle: Optional[str] = Field(default=None, max_length=120)
    displayDescription: Optional[str] = Field(default=None, max_length=500)
    publicTerms: Optional[str] = Field(default=None, max_length=2000)
    applicableChannels: list[str] = Field(default_factory=lambda: ["WEB"])
    applicablePaymentMethods: list[str] = Field(default_factory=list)
    eligibleTiers: list[str] = Field(default_factory=list)
    eligibleUserRegisteredAfter: Optional[str] = None
    assignedUserId: Optional[UUID] = None
    assignedUserIds: list[UUID] = Field(default_factory=list)
    includeProductIds: list[str] = Field(default_factory=list)
    excludeProductIds: list[str] = Field(default_factory=list)
    includeCategoryIds: list[str] = Field(default_factory=list)
    excludeCategoryIds: list[str] = Field(default_factory=list)
    includeBrandIds: list[str] = Field(default_factory=list)
    excludeBrandIds: list[str] = Field(default_factory=list)
    firstOrderOnly: bool = False
    hiddenCode: bool = False
    abandonedCartOnly: bool = False
    birthdayOnly: bool = False
    validityDaysAfterClaim: int = Field(default=0, ge=0)
    stackable: bool = False
    applyOutsideScope: bool = False
    refundPolicy: Literal['NEVER', 'SHOP_FAULT_ONLY', 'ALWAYS'] = 'SHOP_FAULT_ONLY'
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    internalNote: Optional[str] = None
    status: Literal['ACTIVE', 'INACTIVE', 'EXPIRED'] = 'ACTIVE'

    @model_validator(mode="after")
    def validate_voucher_logic(self) -> 'VoucherPayload':
        if self.discountType == 'PERCENT' and self.discountAmount > 100.0:
            raise ValueError("Giá trị phần trăm giảm giá không được vượt quá 100%.")

        start_dt = None
        end_dt = None

        if self.startsAt:
            try:
                clean_start = self.startsAt.replace('T', ' ')
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        start_dt = datetime.strptime(clean_start, fmt)
                        break
                    except ValueError:
                        continue
                if not start_dt:
                    start_dt = datetime.fromisoformat(self.startsAt)
            except Exception:
                raise ValueError("Định dạng ngày bắt đầu (startsAt) không hợp lệ.")

        if self.endsAt:
            try:
                clean_end = self.endsAt.replace('T', ' ')
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        end_dt = datetime.strptime(clean_end, fmt)
                        break
                    except ValueError:
                        continue
                if not end_dt:
                    end_dt = datetime.fromisoformat(self.endsAt)
            except Exception:
                raise ValueError("Định dạng ngày kết thúc (endsAt) không hợp lệ.")

        if start_dt and end_dt and start_dt >= end_dt:
            raise ValueError("Ngày bắt đầu phải trước ngày kết thúc.")

        return self


class VoucherUpdatePayload(BaseModel):
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    discountType: Optional[Literal['FIXED', 'PERCENT']] = None
    discountAmount: Optional[float] = Field(default=None, gt=0)
    minOrderValue: Optional[float] = Field(default=None, ge=0)
    maxDiscount: Optional[float] = Field(default=None, ge=0)
    usageLimit: Optional[int] = Field(default=None, ge=0)
    totalBudgetCap: Optional[float] = Field(default=None, ge=0)
    perUserLimit: Optional[int] = Field(default=None, ge=0)
    perDeviceLimit: Optional[int] = Field(default=None, ge=0)
    perIpLimit: Optional[int] = Field(default=None, ge=0)
    campaignType: Optional[Literal['CONVERSION', 'ACQUISITION', 'RETENTION', 'CUSTOMER_SERVICE', 'LOYALTY', 'FLASH_SALE', 'ABANDONED_CART']] = None
    audienceType: Optional[Literal['PUBLIC', 'NEW_CUSTOMER', 'MEMBER_TIER', 'SPECIFIC_USER', 'HIDDEN', 'ABANDONED_CART']] = None
    displayTitle: Optional[str] = Field(default=None, max_length=120)
    displayDescription: Optional[str] = Field(default=None, max_length=500)
    publicTerms: Optional[str] = Field(default=None, max_length=2000)
    applicableChannels: Optional[list[str]] = None
    applicablePaymentMethods: Optional[list[str]] = None
    redemptionPoints: Optional[int] = Field(default=None, ge=0)
    eligibleTiers: Optional[list[str]] = None
    eligibleUserRegisteredAfter: Optional[str] = None
    assignedUserId: Optional[UUID] = None
    assignedUserIds: Optional[list[UUID]] = None
    includeProductIds: Optional[list[str]] = None
    excludeProductIds: Optional[list[str]] = None
    includeCategoryIds: Optional[list[str]] = None
    excludeCategoryIds: Optional[list[str]] = None
    includeBrandIds: Optional[list[str]] = None
    excludeBrandIds: Optional[list[str]] = None
    firstOrderOnly: Optional[bool] = None
    hiddenCode: Optional[bool] = None
    abandonedCartOnly: Optional[bool] = None
    birthdayOnly: Optional[bool] = None
    validityDaysAfterClaim: Optional[int] = Field(default=None, ge=0)
    stackable: Optional[bool] = None
    applyOutsideScope: Optional[bool] = None
    refundPolicy: Optional[Literal['NEVER', 'SHOP_FAULT_ONLY', 'ALWAYS']] = None
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    internalNote: Optional[str] = None
    status: Optional[Literal['ACTIVE', 'INACTIVE', 'EXPIRED']] = None

    @model_validator(mode="after")
    def validate_voucher_update_logic(self) -> 'VoucherUpdatePayload':
        if self.discountType is not None or self.discountAmount is not None:
            dtype = self.discountType
            damt = self.discountAmount
            if dtype == 'PERCENT' and damt is not None and damt > 100.0:
                raise ValueError("Giá trị phần trăm giảm giá không được vượt quá 100%.")

        start_dt = None
        end_dt = None

        if self.startsAt:
            try:
                clean_start = self.startsAt.replace('T', ' ')
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        start_dt = datetime.strptime(clean_start, fmt)
                        break
                    except ValueError:
                        continue
                if not start_dt:
                    start_dt = datetime.fromisoformat(self.startsAt)
            except Exception:
                raise ValueError("Định dạng ngày bắt đầu (startsAt) không hợp lệ.")

        if self.endsAt:
            try:
                clean_end = self.endsAt.replace('T', ' ')
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        end_dt = datetime.strptime(clean_end, fmt)
                        break
                    except ValueError:
                        continue
                if not end_dt:
                    end_dt = datetime.fromisoformat(self.endsAt)
            except Exception:
                raise ValueError("Định dạng ngày kết thúc (endsAt) không hợp lệ.")

        if start_dt and end_dt and start_dt >= end_dt:
            raise ValueError("Ngày bắt đầu phải trước ngày kết thúc.")

        return self
