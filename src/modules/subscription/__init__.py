"""
subscription: plano e cota diária de tokens (README.md). A API pública é só domínio; a composição
monta o módulo por `src.modules.subscription.container`.
"""
from src.modules.subscription.domain.entities.subscription import Subscription
from src.modules.subscription.domain.events import SubscriptionUpgradedEvent
from src.modules.subscription.domain.exceptions import (
    DailyQuotaExceededError,
    PlantLimitExceededError,
)
from src.modules.subscription.domain.services.garden_quota import IGardenQuota
from src.modules.subscription.domain.services.token_wallet import ITokenWallet
from src.modules.subscription.domain.value_objects.tier import (
    FeatureCost,
    SubscriptionTier,
)

__all__ = [
    "FeatureCost",
    "IGardenQuota",
    "ITokenWallet",
    "PlantLimitExceededError",
    "Subscription",
    "DailyQuotaExceededError",
    "SubscriptionTier",
    "SubscriptionUpgradedEvent",
]
