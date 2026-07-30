from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class FlashSalePayload(BaseModel):
    productId: UUID
    variantId: UUID | None = None
    discountType: str = Field(default="PERCENT")
    discountValue: float = Field(gt=0)
    startsAt: datetime | None = None
    endsAt: datetime | None = None
    quantityLimit: int | None = Field(default=None, ge=1)
    perUserLimit: int | None = Field(default=None, ge=1)
    status: str = Field(default="ACTIVE")

    @model_validator(mode="after")
    def validate_window(self):
        if self.endsAt and self.startsAt and self.endsAt <= self.startsAt:
            raise ValueError("Thời gian kết thúc phải lớn hơn thời gian bắt đầu.")
        self.discountType = self.discountType.upper()
        if self.discountType not in {"FIXED", "PERCENT"}:
            raise ValueError("Kiểu giảm giá không hợp lệ.")
        if self.discountType == "PERCENT" and self.discountValue >= 100:
            raise ValueError("Giảm theo phần trăm phải nhỏ hơn 100%.")
        self.status = self.status.upper()
        if self.status not in {"ACTIVE", "INACTIVE"}:
            raise ValueError("Trạng thái flash sale không hợp lệ.")
        return self
