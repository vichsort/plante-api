from abc import ABC, abstractmethod
from datetime import datetime

from src.modules.subscription.domain.entities.subscription import Subscription
from src.modules.subscription.domain.policies.subscription_policy import (
    SubscriptionPolicy,
)
from src.modules.subscription.domain.ports.unit_of_work import ISubscriptionUnitOfWork
from src.shared.domain import UserId


class IGardenQuota(ABC):
    """Quantas plantas o plano ativo do usuário deixa ter no jardim."""

    @abstractmethod
    async def ensure_can_add_plant(self, user_id: UserId, plants_in_garden: int, now: datetime) -> None:
        """`plants_in_garden` = plantas ativas hoje. Lança `PlantLimitExceededError` no limite."""
        ...


class GardenQuota(IGardenQuota):
    def __init__(self, uow: ISubscriptionUnitOfWork) -> None:
        self.uow = uow

    async def ensure_can_add_plant(self, user_id: UserId, plants_in_garden: int, now: datetime) -> None:
        async with self.uow as uow:
            subscription = await uow.subscriptions.get(user_id) or Subscription.free_for(user_id)
        SubscriptionPolicy.enforce_can_add_to_garden(subscription, plants_in_garden, now)
