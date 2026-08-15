from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.api.schemas.media_reference import normalize_media_reference, normalize_media_reference_list


class ReviewRequest(BaseModel):
    userName: str = Field(min_length=1, max_length=255)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1, max_length=2000)
    mediaUrls: list[str] = Field(default_factory=list, max_length=6)

    _normalize_media = field_validator("mediaUrls", mode="before")(normalize_media_reference_list)


class ReviewUpdateRequest(BaseModel):
    userName: str = Field(min_length=1, max_length=255)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1, max_length=2000)
    mediaUrls: list[str] = Field(default_factory=list, max_length=6)

    _normalize_media = field_validator("mediaUrls", mode="before")(normalize_media_reference_list)


class VideoCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
    parentId: UUID | None = None
    replyToUserName: str | None = Field(default=None, max_length=120)


class ProductImageCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
    imageUrl: str | None = None
    parentId: UUID | None = None
    replyToUserName: str | None = Field(default=None, max_length=120)

    _normalize_media = field_validator("imageUrl", mode="before")(normalize_media_reference)


class ProductQuestionRequest(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
    parentId: UUID | None = None
    replyToUserName: str | None = Field(default=None, max_length=120)


class VideoViewHeartbeatRequest(BaseModel):
    watchedSeconds: int = Field(ge=1, le=30)
    positionSeconds: float | None = Field(default=None, ge=0)
    visible: bool = True
