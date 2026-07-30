from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FactEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(min_length=1, max_length=180)
    source_type: str = Field(min_length=1, max_length=80)
    source_id: str = Field(min_length=1, max_length=180)
    source_version: str | None = Field(default=None, max_length=80)
    visibility_scope: Literal["PUBLIC", "USER"]
    fields: dict[str, Any]


class ResponseCard(BaseModel):
    type: Literal["product", "used_product"] = "product"
    id: str
    reason: str | None = None


class ResponseSource(BaseModel):
    type: str
    id: str
    updated_at: str | None = None


class HandoverInfo(BaseModel):
    recommended: bool = True
    reason: str
    phone: str | None = None
    email: str | None = None
    display_text: str | None = None
    can_create_ticket: bool = False
    support_request_code: str | None = None


class VerificationResult(BaseModel):
    passed: bool
    errors: list[str] = Field(default_factory=list)
    cards: list[ResponseCard] = Field(default_factory=list)
    sources: list[ResponseSource] = Field(default_factory=list)
