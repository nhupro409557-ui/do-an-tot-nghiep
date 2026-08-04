from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SupplierPaymentPayload(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    paymentDate: datetime | None = None
    method: str = Field(default="BANK_TRANSFER", pattern="^(CASH|BANK_TRANSFER|OTHER)$")
    referenceNo: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)


class AccountPayableAdjustmentPayload(BaseModel):
    type: Literal["DEBIT", "CREDIT"]
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    reason: str = Field(min_length=3, max_length=500)


class SupplierPaymentReversalPayload(BaseModel):
    paymentId: UUID
    reason: str = Field(min_length=3, max_length=500)
