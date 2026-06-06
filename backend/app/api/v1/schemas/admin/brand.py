from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class BrandPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=80)
    slug: str | None = Field(default=None, max_length=120)
    order: int = Field(default=0, ge=0)
    isActive: bool = True
    categoryIds: list[UUID] = Field(default_factory=list)
    logoUrl: str | None = None
    logoAltText: str | None = Field(default=None, max_length=255)
    landingTitle: str | None = Field(default=None, max_length=255)
    seoTitle: str | None = Field(default=None, max_length=255)
    seoDescription: str | None = None

class BrandCodeCheckPayload(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    excludeId: UUID | None = None

class BrandImportItem(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=80)
    logoUrl: str | None = None
    order: int = Field(default=0, ge=0)

class BrandImportPayload(BaseModel):
    items: list[BrandImportItem] = Field(min_length=1, max_length=500)
    mode: str = Field(default="skip", pattern="^(skip|upsert)$")
    sourceFilename: str | None = Field(default=None, max_length=255)

class BrandStatusPayload(BaseModel):
    isActive: bool

class BrandBulkStatusPayload(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=200)
    isActive: bool
