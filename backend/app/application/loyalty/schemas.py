from uuid import UUID

from pydantic import BaseModel, Field


class RedeemPointsRequest(BaseModel):
    order_id: UUID
    points: int = Field(gt=0, le=1_000_000)


class RedeemPointsResponse(BaseModel):
    user_id: UUID
    order_id: UUID
    redeemed_points: int
    balance_after: int = Field(ge=0)

