from dataclasses import dataclass


@dataclass(frozen=True)
class DomainError(Exception):
    message: str


class UserNotFoundError(DomainError):
    pass


class LoyaltyWalletClosedError(DomainError):
    pass


class InsufficientPointsError(DomainError):
    pass
