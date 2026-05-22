from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


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


class AIAssistantRequest(BaseModel):
    conversation_id: UUID
    message: str = Field(min_length=1, max_length=2000)
    dynamic_context: DynamicAIContext
    model_provider: Literal["OPENAI", "GEMINI"] = "OPENAI"
    model_name: str = Field(default="gpt-4.1-mini", min_length=1, max_length=100)


class AIAssistantResponse(BaseModel):
    conversation_id: UUID
    answer: str
    refused: bool = False
    refusal_reason: str | None = None
    intent: str | None = None
    handover_recommended: bool = False
    sources: list[str] = Field(default_factory=list)
    recommended_products: list[dict] = Field(default_factory=list, max_length=10)
