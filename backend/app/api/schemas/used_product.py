from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

class UserBuybackRequestPayload(BaseModel):
    productId: UUID
    variantId: UUID | None = None
    imei: str = Field(min_length=15, max_length=80)
    expectedPrice: Decimal | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("imei")
    @classmethod
    def validate_imei(cls, value: str) -> str:
        normalized = "".join(character for character in value if character.isdigit())
        if len(normalized) != 15:
            raise ValueError("IMEI phải gồm đúng 15 chữ số.")
        return normalized
