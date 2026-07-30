from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class PurchaseOrderLinePayload(BaseModel):
    productId: UUID
    variantId: UUID | None = None
    quantity: int = Field(gt=0, le=100000)
    unitCost: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=500)


class PurchaseOrderPayload(BaseModel):
    code: str = Field(min_length=1, max_length=120)
    supplierId: UUID
    expectedDate: date | None = None
    note: str | None = Field(default=None, max_length=500)
    discountAmount: float = Field(default=0, ge=0)
    shippingFee: float = Field(default=0, ge=0)
    lines: list[PurchaseOrderLinePayload] = Field(min_length=1, max_length=100)


class PurchaseOrderStatusPayload(BaseModel):
    status: str = Field(pattern="^(PENDING_APPROVAL|APPROVED|CANCELLED)$")
    note: str | None = Field(default=None, max_length=500)
