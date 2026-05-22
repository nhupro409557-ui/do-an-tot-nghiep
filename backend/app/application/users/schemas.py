from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.users.entities import LoyaltyWalletStatus, UserStatus


class DeleteAccountConfirmation(StrEnum):
    DELETE_ACCOUNT = "DELETE_ACCOUNT"


class DeleteAccountRequest(BaseModel):
    confirmation: str = Field(min_length=14, max_length=14)

    @field_validator("confirmation")
    @classmethod
    def confirmation_must_match(cls, value: str) -> str:
        if value != DeleteAccountConfirmation.DELETE_ACCOUNT:
            raise ValueError("Confirmation must be DELETE_ACCOUNT.")
        return value


class DeleteAccountResponse(BaseModel):
    user_id: UUID
    status: UserStatus
    loyalty_wallet_status: LoyaltyWalletStatus
    revoked_points: int = Field(ge=0)

