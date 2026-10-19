from abc import ABC, abstractmethod
from datetime import datetime

from src.modules.quota.domain.entities.quota import Quota
from src.modules.quota.domain.policies.quota_policy import (
    QuotaPolicy,
)
from src.modules.quota.domain.ports.unit_of_work import IQuotaUnitOfWork
from src.shared.domain import UserId


class IGardenQuota(ABC):
    """How many plants the user's active quota allows in the garden."""

    @abstractmethod
    async def ensure_can_add_plant(self, user_id: UserId, plants_in_garden: int, now: datetime) -> None:
        """`plants_in_garden` = plantas ativas hoje. Lança `PlantLimitExceededError` no limite."""
        ...


class GardenQuota(IGardenQuota):
    def __init__(self, uow: IQuotaUnitOfWork) -> None:
        self.uow = uow

    async def ensure_can_add_plant(self, user_id: UserId, plants_in_garden: int, now: datetime) -> None:
        async with self.uow as uow:
            quota = await uow.quotas.get(user_id) or Quota.standard_for(user_id)
        QuotaPolicy.enforce_can_add_to_garden(quota, plants_in_garden, now)
