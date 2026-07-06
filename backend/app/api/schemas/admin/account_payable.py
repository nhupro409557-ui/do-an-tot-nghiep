from datetime import datetime

from pydantic import BaseModel, Field


class SupplierPaymentPayload(BaseModel):
    amount: float = Field(gt=0)
    paymentDate: datetime | None = None
    method: str = Field(default="BANK_TRANSFER", pattern="^(CASH|BANK_TRANSFER|OTHER)$")
    referenceNo: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)


class AccountPayableAdjustmentPayload(BaseModel):
    principalAmount: float = Field(ge=0)
    paymentTermDays: int = Field(default=0, ge=0, le=365)
    dueDate: datetime | None = None
    note: str | None = Field(default=None, max_length=500)
