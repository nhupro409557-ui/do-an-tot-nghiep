from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


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
    cycleCountDays: int | None = Field(default=None, ge=1, le=365)

class VariantInventoryPayload(BaseModel):
    quantity: int = Field(ge=0)
    referenceCode: str = Field(min_length=1, max_length=120)
    transactionType: str = Field(default="ADJUSTMENT", pattern="^(RECEIPT|ADJUSTMENT|SALE|RETURN|REVERSAL)$")
    reason: str = Field(default="MANUAL_SET", max_length=80)
    note: str | None = Field(default=None, max_length=500)
