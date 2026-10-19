from abc import ABC, abstractmethod

from src.modules.quota.domain.entities.quota import Quota
from src.shared.domain import UserId


class IQuotaRepository(ABC):
    @abstractmethod
    async def get(self, user_id: UserId) -> Quota | None:
        """The stored quota, or `None` (the user is standard with a full quota)."""
        ...

    @abstractmethod
    async def lock(self, user_id: UserId) -> Quota:
        """
        The quota locked until the end of the transaction, created as standard if missing. Two
        concurrent charges for the same user wait for each other instead of one overwriting the
        other. Raises `UserNotFoundError` if the user has no account.
        """
        ...

    @abstractmethod
    async def save(self, quota: Quota) -> None:
        ...
