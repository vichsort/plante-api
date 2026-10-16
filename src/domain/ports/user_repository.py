from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.user import User
from src.domain.value_objects.subscription_tier import SubscriptionTier
from src.shared.domain import UserId


class IUserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> User:
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> User | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    async def update_subscription(
        self,
        user_id: UserId,
        tier: SubscriptionTier,
        expires_at: datetime,
    ) -> None:
        ...