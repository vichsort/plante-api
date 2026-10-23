"""
quota: quota level and daily AI tokens (README.md). The public API is domain only; the composition
builds the module through `src.modules.quota.container`.
"""
from src.modules.quota.domain.entities.quota import Quota
from src.modules.quota.domain.exceptions import (
    DailyQuotaExceededError,
    PlantLimitExceededError,
    ServiceDailyLimitError,
)
from src.modules.quota.domain.services.garden_quota import IGardenQuota
from src.modules.quota.domain.services.provider_budget import IProviderBudget
from src.modules.quota.domain.services.token_wallet import ITokenWallet
from src.modules.quota.domain.use_cases.grant_extended_quota import (
    MAX_GRANT_DAYS,
    GrantExtendedQuotaInputDTO,
)
from src.modules.quota.domain.value_objects.level import (
    FeatureCost,
    LevelLimits,
    QuotaLevel,
    QuotaLimits,
)

__all__ = [
    "MAX_GRANT_DAYS",
    "GrantExtendedQuotaInputDTO",
    "FeatureCost",
    "IGardenQuota",
    "IProviderBudget",
    "ITokenWallet",
    "PlantLimitExceededError",
    "Quota",
    "DailyQuotaExceededError",
    "LevelLimits",
    "QuotaLevel",
    "QuotaLimits",
    "ServiceDailyLimitError",
]
