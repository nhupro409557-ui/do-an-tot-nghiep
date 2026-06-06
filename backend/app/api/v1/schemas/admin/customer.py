from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class CustomerTagsPayload(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=20)

class CustomerBulkTagsPayload(BaseModel):
    userIds: list[UUID] = Field(min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=20)

class CustomerNotePayload(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

class CustomerLoyaltyAdjustmentPayload(BaseModel):
    delta: int = Field(ge=-500000, le=500000)
    reason: str = Field(min_length=3, max_length=255)

class CustomerVoucherIssuePayload(BaseModel):
    voucherId: UUID
    note: str | None = Field(default=None, max_length=255)

class CustomerBulkStatusPayload(BaseModel):
    userIds: list[UUID] = Field(min_length=1, max_length=200)
    status: str = Field(pattern="^(ACTIVE|SUSPENDED)$")
