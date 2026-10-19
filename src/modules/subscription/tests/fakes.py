"""Dublês de `ITokenWallet` e `IGardenQuota` para os testes de quem consome a cota (outros módulos)."""
from dataclasses import dataclass, field
from datetime import datetime

from src.modules.subscription.domain.entities.subscription import Subscription
from src.modules.subscription.domain.policies.subscription_policy import (
    SubscriptionPolicy,
)
from src.modules.subscription.domain.services.garden_quota import IGardenQuota
from src.modules.subscription.domain.services.token_wallet import ITokenWallet
from src.modules.subscription.domain.value_objects.tier import (
    FeatureCost,
    SubscriptionTier,
)
from src.shared.domain import UserId


@dataclass
class FakeTokenWallet(ITokenWallet):
    """
    Uma assinatura FREE em memória, com as regras de verdade (`SubscriptionPolicy`); o dia é o
    da chamada, então `used_today` vale para "hoje". `charges` guarda as cobranças, na ordem.
    """
    used_today: int = 0
    charges: list[tuple[UserId, FeatureCost]] = field(default_factory=list)

    def _subscription(self, user_id: UserId, now: datetime) -> Subscription:
        return Subscription(user_id, SubscriptionTier.FREE, tokens_used_today=self.used_today, tokens_day=now.date())

    async def ensure_can_identify(self, user_id: UserId, now: datetime) -> None:
        SubscriptionPolicy.enforce_can_identify_plant(self._subscription(user_id, now), now, now.date())

    async def ensure_can_diagnose(self, user_id: UserId, now: datetime) -> None:
        SubscriptionPolicy.enforce_can_diagnose(self._subscription(user_id, now), now, now.date())

    async def can_enrich_diagnosis(self, user_id: UserId, now: datetime) -> bool:
        return SubscriptionPolicy.can_enrich_diagnosis(self._subscription(user_id, now), now, now.date())

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
        subscription = Subscription(user_id, self.tier, expires_at=datetime.max.replace(tzinfo=now.tzinfo))
        SubscriptionPolicy.enforce_can_add_to_garden(subscription, plants_in_garden, now)
