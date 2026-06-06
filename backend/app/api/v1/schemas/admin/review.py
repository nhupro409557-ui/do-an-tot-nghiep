from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class ReviewStatusPayload(BaseModel):
    status: str | None = Field(default=None, pattern="^(PENDING|PUBLISHED|HIDDEN|REJECTED)$")
    moderationNote: str | None = Field(default=None, max_length=1000)
    shopReply: str | None = Field(default=None, max_length=2000)
    flaggedReason: str | None = Field(default=None, max_length=1000)
    isSpam: bool | None = None
    spamReason: str | None = Field(default=None, max_length=1000)
