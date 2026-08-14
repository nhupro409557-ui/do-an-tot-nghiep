from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.application.ai.contracts import HandoverInfo, ResponseCard, ResponseSource


class CartContextItem(BaseModel):
    product_id: UUID | str
    name: str = Field(min_length=1, max_length=255)
    quantity: int = Field(gt=0, le=99)
    price: float = Field(ge=0)


class ViewedProductContext(BaseModel):
    product_id: UUID | str
    name: str = Field(min_length=1, max_length=255)
    viewed_at: str = Field(min_length=10, max_length=40)


class LoyaltyContext(BaseModel):
    tier: Literal["MEMBER", "SILVER", "GOLD", "DIAMOND"]
    points_balance: int = Field(ge=0)
    wallet_status: Literal["ACTIVE", "CLOSED"]


class DynamicAIContext(BaseModel):
    cart_items: list[CartContextItem] = Field(default_factory=list, max_length=50)
    viewed_products: list[ViewedProductContext] = Field(default_factory=list, max_length=50)
    loyalty: LoyaltyContext | None = None


class PageContext(BaseModel):
    product_id: UUID | str | None = None
    cart_item_ids: list[UUID | str] = Field(default_factory=list, max_length=50)


class AIAssistantRequest(BaseModel):
    conversation_id: UUID
    conversation_token: str | None = Field(default=None, min_length=20, max_length=2000)
    message: str = Field(min_length=1, max_length=2000)
    dynamic_context: DynamicAIContext = Field(default_factory=DynamicAIContext)
    page_context: PageContext | None = None
    client_capabilities: list[str] = Field(default_factory=list, max_length=20)
    model_provider: Literal["OPENAI", "GEMINI"] = "GEMINI"
    model_name: str = Field(default="gemini-3.5-flash", min_length=1, max_length=100)


class AIAssistantResponse(BaseModel):
    response_id: UUID = Field(default_factory=uuid4)
    version: Literal["1", "2"] = "1"
    conversation_id: UUID
    answer: str
    refused: bool = False
    refusal_reason: str | None = None
    intent: str | None = None
    handover_recommended: bool = False
    sources: list[str] = Field(default_factory=list)
    recommended_products: list[dict] = Field(default_factory=list, max_length=10)
    answer_mode: Literal[
        "GEMINI",
        "GROUNDED_GENERATION",
        "DETERMINISTIC",
        "DATABASE_FALLBACK",
        "POLICY_REFUSAL",
    ] = "GEMINI"
    provider_used: Literal["GEMINI", "GROQ", "SYSTEM"] = "GEMINI"
    model_name: str | None = None
    fallback_reason: str | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)
    needs_clarification: bool = False
    clarification_question: str | None = None
    cards: list[ResponseCard] = Field(default_factory=list, max_length=10)
    source_details: list[ResponseSource] = Field(default_factory=list, max_length=20)
    handover: HandoverInfo | None = None
    verification_passed: bool | None = None


class AIAssistantFeedbackRequest(BaseModel):
    response_id: UUID
    conversation_id: UUID
    conversation_token: str = Field(min_length=20, max_length=2000)
    helpful: bool
    reason: str | None = Field(default=None, max_length=500)


class AIAssistantFeedbackResponse(BaseModel):
    saved: bool
    handover_recommended: bool = False
    handover: HandoverInfo | None = None


class AIConversationSessionResponse(BaseModel):
    conversation_id: UUID
    conversation_token: str
    expires_at: datetime
