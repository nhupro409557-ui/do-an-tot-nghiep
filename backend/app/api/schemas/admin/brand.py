from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.api.schemas.media_reference import normalize_media_reference


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
    version: int | None = Field(default=None, ge=1)

    _normalize_media = field_validator("logoUrl", mode="before")(normalize_media_reference)

class BrandCodeCheckPayload(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    excludeId: UUID | None = None

class BrandStatusPayload(BaseModel):
    isActive: bool
    version: int | None = Field(default=None, ge=1)

class BrandBulkStatusPayload(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=200)
    isActive: bool
    versions: dict[UUID, int] | None = Field(default=None)
