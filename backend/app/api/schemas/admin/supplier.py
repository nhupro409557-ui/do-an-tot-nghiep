from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SupplierPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=80)
    contactName: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    address: str | None = None
    taxCode: str | None = Field(default=None, max_length=80)
    website: str | None = Field(default=None, max_length=255)
    note: str | None = None
    isActive: bool = True


class SupplierCodeCheckPayload(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    excludeId: UUID | None = None


class SupplierStatusPayload(BaseModel):
    isActive: bool


class SupplierBulkStatusPayload(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=200)
    isActive: bool
