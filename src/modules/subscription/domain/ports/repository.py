from abc import ABC, abstractmethod

from src.modules.subscription.domain.entities.subscription import Subscription
from src.shared.domain import UserId


class ISubscriptionRepository(ABC):
    @abstractmethod
    async def get(self, user_id: UserId) -> Subscription | None:
        """A assinatura gravada, ou `None` (o usuário é FREE com a cota cheia)."""
        ...

    @abstractmethod
    async def lock(self, user_id: UserId) -> Subscription:
        """
        A assinatura travada até o fim da transação, criada como FREE se ainda não existir. Duas
        cobranças simultâneas do mesmo usuário esperam uma pela outra em vez de uma sobrescrever a
        outra. Lança `UserNotFoundError` se o usuário não tem conta.
        """
        ...

    @abstractmethod
    async def save(self, subscription: Subscription) -> None:
        ...
