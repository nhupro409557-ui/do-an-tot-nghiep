from uuid import UUID

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    userName: str = Field(min_length=1, max_length=255)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1, max_length=2000)
    mediaUrls: list[str] = Field(default_factory=list, max_length=6)


class ReviewUpdateRequest(BaseModel):
    userName: str = Field(min_length=1, max_length=255)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1, max_length=2000)
    mediaUrls: list[str] = Field(default_factory=list, max_length=6)


class VideoCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
    parentId: UUID | None = None
    replyToUserName: str | None = Field(default=None, max_length=120)


class ProductImageCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
    imageUrl: str | None = None
    parentId: UUID | None = None
    replyToUserName: str | None = Field(default=None, max_length=120)


class VideoViewHeartbeatRequest(BaseModel):
    watchedSeconds: int = Field(ge=1, le=30)
    positionSeconds: float | None = Field(default=None, ge=0)
    visible: bool = True
