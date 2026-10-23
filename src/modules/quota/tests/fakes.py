"""`ITokenWallet` and `IGardenQuota` doubles for the tests of the quota's consumers (other modules)."""
from dataclasses import dataclass, field
from datetime import datetime

from src.modules.quota.domain.entities.quota import Quota
from src.modules.quota.domain.policies.quota_policy import QuotaPolicy
from src.modules.quota.domain.services.garden_quota import IGardenQuota
from src.modules.quota.domain.services.token_wallet import ITokenWallet
from src.modules.quota.domain.value_objects.level import (
    FeatureCost,
    LevelLimits,
    QuotaLevel,
    QuotaLimits,
)
from src.shared.domain import UserId

# The settings defaults: standard 3 plants and 3 tokens a day, extended 10 and 10
LIMITS = LevelLimits(standard=QuotaLimits(max_plants=3, daily_tokens=3), extended=QuotaLimits(max_plants=10, daily_tokens=10))
POLICY = QuotaPolicy(LIMITS)


@dataclass
class FakeTokenWallet(ITokenWallet):
    """
    A standard quota in memory, with the real rules (`QuotaPolicy`); the day is the call's, so
    `used_today` counts for "today". `charges` keeps the charges, in order.
    """
    used_today: int = 0
    charges: list[tuple[UserId, FeatureCost]] = field(default_factory=list)

    def _quota(self, user_id: UserId, now: datetime) -> Quota:
        return Quota(user_id, QuotaLevel.STANDARD, tokens_used_today=self.used_today, tokens_day=now.date())

    async def ensure_can_identify(self, user_id: UserId, now: datetime) -> None:
        POLICY.enforce_can_identify_plant(self._quota(user_id, now), now, now.date())

    async def ensure_can_diagnose(self, user_id: UserId, now: datetime) -> None:
        POLICY.enforce_can_diagnose(self._quota(user_id, now), now, now.date())

    async def can_enrich_diagnosis(self, user_id: UserId, now: datetime) -> bool:
        return POLICY.can_enrich_diagnosis(self._quota(user_id, now), now, now.date())

    async def charge(self, user_id: UserId, cost: FeatureCost, now: datetime) -> None:
        self.used_today += cost.value
        self.charges.append((user_id, cost))

    @property
    def charged(self) -> int:
        return sum(cost.value for _, cost in self.charges)


@dataclass
class FakeGardenQuota(IGardenQuota):
    """The garden limit of one level (standard by default)."""
    level: QuotaLevel = QuotaLevel.STANDARD

    async def ensure_can_add_plant(self, user_id: UserId, plants_in_garden: int, now: datetime) -> None:
        expires_at = datetime.max.replace(tzinfo=now.tzinfo) if self.level is QuotaLevel.EXTENDED else None
        POLICY.enforce_can_add_to_garden(Quota(user_id, self.level, expires_at), plants_in_garden, now)
