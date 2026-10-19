"""Dublês de `ITokenWallet` e `IGardenQuota` para os testes de quem consome a cota (outros módulos)."""
from dataclasses import dataclass, field
from datetime import datetime

from src.modules.quota.domain.entities.quota import Quota
from src.modules.quota.domain.policies.quota_policy import (
    QuotaPolicy,
)
from src.modules.quota.domain.services.garden_quota import IGardenQuota
from src.modules.quota.domain.services.token_wallet import ITokenWallet
from src.modules.quota.domain.value_objects.tier import (
    FeatureCost,
    SubscriptionTier,
)
from src.shared.domain import UserId


@dataclass
class FakeTokenWallet(ITokenWallet):
    """
    Uma assinatura FREE em memória, com as regras de verdade (`QuotaPolicy`); o dia é o
    da chamada, então `used_today` vale para "hoje". `charges` guarda as cobranças, na ordem.
    """
    used_today: int = 0
    charges: list[tuple[UserId, FeatureCost]] = field(default_factory=list)

    def _quota(self, user_id: UserId, now: datetime) -> Quota:
        return Quota(user_id, SubscriptionTier.FREE, tokens_used_today=self.used_today, tokens_day=now.date())

    async def ensure_can_identify(self, user_id: UserId, now: datetime) -> None:
        QuotaPolicy.enforce_can_identify_plant(self._quota(user_id, now), now, now.date())

    async def ensure_can_diagnose(self, user_id: UserId, now: datetime) -> None:
        QuotaPolicy.enforce_can_diagnose(self._quota(user_id, now), now, now.date())

    async def can_enrich_diagnosis(self, user_id: UserId, now: datetime) -> bool:
        return QuotaPolicy.can_enrich_diagnosis(self._quota(user_id, now), now, now.date())

    async def charge(self, user_id: UserId, cost: FeatureCost, now: datetime) -> None:
        self.used_today += cost.value
        self.charges.append((user_id, cost))

    @property
    def charged(self) -> int:
        return sum(cost.value for _, cost in self.charges)


@dataclass
class FakeGardenQuota(IGardenQuota):
    """O limite do jardim de um plano (FREE por padrão)."""
    tier: SubscriptionTier = SubscriptionTier.FREE

    async def ensure_can_add_plant(self, user_id: UserId, plants_in_garden: int, now: datetime) -> None:
        quota = Quota(user_id, self.tier, expires_at=datetime.max.replace(tzinfo=now.tzinfo))
        QuotaPolicy.enforce_can_add_to_garden(quota, plants_in_garden, now)
