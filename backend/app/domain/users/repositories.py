from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class UserRepository(ABC):
    @abstractmethod
    async def get_deletable_user_for_update(self, user_id: UUID) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def get_active_user_for_update(self, user_id: UUID) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def save(self, user: Any) -> None:
        raise NotImplementedError


class LoyaltyRepository(ABC):
    @abstractmethod
    async def add_revoke_transaction(
        self,
        *,
        user_id: UUID,
        points: int,
        balance_before: int,
        reason: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def add_redeem_transaction(
        self,
        *,
        user_id: UUID,
        order_id: UUID,
        points: int,
        balance_before: int,
        balance_after: int,
        reason: str,
    ) -> None:
        raise NotImplementedError
