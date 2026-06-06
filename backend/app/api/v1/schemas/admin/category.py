from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class CategoryPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=80)
    slug: str | None = Field(default=None, max_length=120)
    icon: str | None = Field(default=None, max_length=80)
    iconUrl: str | None = None
    bannerUrl: str | None = None
    parentId: UUID | None = None
    order: int = Field(default=0, ge=0)
    isActive: bool = True
    status: str = Field(default="ACTIVE", pattern="^(DRAFT|PENDING_REVIEW|APPROVED|ACTIVE|INACTIVE|REJECTED)$")
    seoTitle: str | None = Field(default=None, max_length=255)
    seoDescription: str | None = None
    seoKeywords: str | None = None
    specFields: list[dict] = Field(default_factory=list)
    filterConfig: list[dict] = Field(default_factory=list)
    inventoryPolicy: dict = Field(default_factory=dict)
    warrantyPolicy: dict = Field(default_factory=dict)
    allowSpecTypeMigration: bool = False
    version: int | None = Field(default=None, ge=1)

class CategorySlugCheckPayload(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    excludeId: UUID | None = None

class CategoryReorderItem(BaseModel):
    id: UUID
    order: int = Field(ge=0)
    parentId: UUID | None = None

class CategoryReorderPayload(BaseModel):
    items: list[CategoryReorderItem] = Field(min_length=1)

class CategoryBulkPayload(BaseModel):
    items: list[CategoryReorderItem] | None = Field(default=None, min_length=1)
    status: str | None = Field(default=None, pattern="^(DRAFT|ACTIVE|INACTIVE)$")
    ids: list[UUID] | None = Field(default=None, min_length=1, max_length=200)
