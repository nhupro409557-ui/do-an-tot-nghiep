from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELETED = "DELETED"


class LoyaltyWalletStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class LoyaltyTransactionType(StrEnum):
    EARN = "EARN"
    REDEEM = "REDEEM"
    REFUND = "REFUND"
    REVOKE = "REVOKE"
    ADJUST = "ADJUST"


class UserEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    status: UserStatus
    loyalty_points_balance: int = Field(ge=0)
    loyalty_wallet_status: LoyaltyWalletStatus

