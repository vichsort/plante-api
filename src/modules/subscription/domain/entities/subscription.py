from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from src.modules.subscription.domain.value_objects.tier import (
    FeatureCost,
    SubscriptionTier,
)
from src.shared.domain import UserId


@dataclass(slots=True)
class Subscription:
    """
    Plano e cota diária de tokens de um usuário. Quem nunca teve linha gravada é FREE com a cota
    cheia (`free_for`): o cadastro não precisa criar nada aqui.
    """

    user_id: UserId
    tier: SubscriptionTier
    expires_at: datetime | None = None
    tokens_used_today: int = 0
    # Dia local a que `tokens_used_today` se refere: em outro dia o contador vale zero
    tokens_day: date | None = None

    def __post_init__(self) -> None:
        if self.tokens_used_today < 0:
            raise ValueError("tokens_used_today cannot be negative.")
        if self.tier == SubscriptionTier.PRO and self.expires_at is None:
            raise ValueError("PRO subscription requires an expiration date.")

    @classmethod
    def free_for(cls, user_id: UserId) -> Subscription:
        return cls(user_id=user_id, tier=SubscriptionTier.FREE)

    def tokens_used_on(self, today: date) -> int:
        """A cota é diária: o contador gravado só vale no dia a que se refere."""
        return self.tokens_used_today if self.tokens_day == today else 0

    def consume_tokens(self, cost: FeatureCost, today: date) -> None:
        """Zera ao virar o dia na primeira cobrança, sem cron (quem decide se pode é a política)."""
        self.tokens_used_today = self.tokens_used_on(today) + cost.value
        self.tokens_day = today

    def upgrade_to_pro(self, expires_at: datetime, current_time: datetime) -> None:
        if expires_at <= current_time:
            raise ValueError("expires_at must be a future datetime.")
        self.tier = SubscriptionTier.PRO
        self.expires_at = expires_at
        self.tokens_used_today = 0  # o upgrade começa com a cota do PRO cheia

    def is_pro(self, current_time: datetime) -> bool:
        return (
            self.tier == SubscriptionTier.PRO
            and self.expires_at is not None
            and current_time < self.expires_at
        )

    def active_tier(self, current_time: datetime) -> SubscriptionTier:
        """PRO vencido conta como FREE."""
        return SubscriptionTier.PRO if self.is_pro(current_time) else SubscriptionTier.FREE
