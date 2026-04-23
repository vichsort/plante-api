from abc import ABC, abstractmethod
from src.domain.entities.user import User
from datetime import datetime
from src.domain.value_objects.subscription_tier import SubscriptionTier

class IUserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> User:
        ...

    @abstractmethod
    async def get_by_id(self, user_id: int) -> User | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    async def update_fcm_token(self, user_id: int, fcm_token: str) -> None:
        """Atualizado sempre que o app reinicia e gera novo token."""
        ...

    @abstractmethod
    async def update_subscription(
        self,
        user_id: int,
        tier: SubscriptionTier,
        expires_at: datetime,
    ) -> None:
        ...