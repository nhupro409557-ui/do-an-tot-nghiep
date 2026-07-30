from dataclasses import dataclass
from fastapi import HTTPException


class BusinessException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        super().__init__(
            status_code=status_code,
            detail={
                "code": code,
                "message": message,
                "details": details or {}
            }
        )


@dataclass(frozen=True)
class DomainError(Exception):
    message: str


class UserNotFoundError(DomainError):
    pass


class LoyaltyWalletClosedError(DomainError):
    pass


class InsufficientPointsError(DomainError):
    pass

