from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class ContentCommentPayload(BaseModel):
    id: str | None = Field(default=None, max_length=80)
    userName: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=1000)
    parentId: str | None = Field(default=None, max_length=80)
    isHidden: bool = False

class ContentPayload(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    contentType: str = Field(default="VIDEO", max_length=30)
    videoSource: str = Field(default="UPLOAD", max_length=30)
    videoCategory: str = Field(default="PRODUCT", max_length=60)
    status: str = Field(default="DRAFT", max_length=30)
    videoUrl: str | None = None
    thumbnailUrl: str | None = None
    bannerImageUrl: str | None = None
    contentBody: str = ""
    ctaLabel: str | None = Field(default=None, max_length=160)
    ctaUrl: str | None = None
    productIds: list[str] = Field(default_factory=list)
    categoryIds: list[str] = Field(default_factory=list)
    comments: list[ContentCommentPayload] = Field(default_factory=list)
    likeCount: int = Field(default=0, ge=0)
    viewCount: int = Field(default=0, ge=0)
    sortOrder: int = Field(default=0, ge=0)
    scheduledAt: str | None = None
    publishedAt: str | None = None
    isActive: bool = True
    version: int | None = Field(default=None, ge=1)

class AdminVideoCommentReplyPayload(BaseModel):
    body: str = Field(min_length=1, max_length=1000)

class AdminVideoCommentVisibilityPayload(BaseModel):
    isHidden: bool = True
