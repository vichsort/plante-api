from datetime import date, datetime

from src.modules.quota.domain.entities.quota import Quota
from src.modules.quota.domain.exceptions import (
    DailyQuotaExceededError,
    PlantLimitExceededError,
)
from src.modules.quota.domain.value_objects.level import (
    FeatureCost,
    LevelLimits,
    QuotaLimits,
)


class QuotaPolicy:
    """
    Quota rules. The **active** level counts (`Quota.active_level`): an expired extended quota is
    standard. The token quota is daily, on the local day (`LocalCalendar`). The limits of each level
    come from configuration.
    """

    def __init__(self, limits: LevelLimits) -> None:
        self.limits = limits

    def _limits(self, quota: Quota, now: datetime) -> QuotaLimits:
        return self.limits.of(quota.active_level(now))

    def can_spend(self, quota: Quota, cost: FeatureCost, now: datetime, today: date) -> bool:
        return self._limits(quota, now).can_consume(cost, quota.tokens_used_on(today))

    def _enforce_can_spend(self, quota: Quota, cost: FeatureCost, now: datetime, today: date) -> None:
        if not self.can_spend(quota, cost, now, today):
            raise DailyQuotaExceededError(
                quota=quota.active_level(now),
                used_today=quota.tokens_used_on(today),
                daily_limit=self._limits(quota, now).daily_tokens,
            )

    def enforce_can_identify_plant(self, quota: Quota, now: datetime, today: date) -> None:
        """Tokens for one identification. The garden limit is not checked: identifying adds no plant."""
        self._enforce_can_spend(quota, FeatureCost.IDENTIFY, now, today)

    def enforce_can_diagnose(self, quota: Quota, now: datetime, today: date) -> None:
        """Tokens for the basic diagnosis (the Gemini add-on is charged apart, if it fits)."""
        self._enforce_can_spend(quota, FeatureCost.DIAGNOSIS, now, today)

    def can_enrich_diagnosis(self, quota: Quota, now: datetime, today: date) -> bool:
        """Do the diagnosis and the Gemini add-on both fit? If not, the diagnosis is Kindwise only."""
        remaining = self._limits(quota, now).remaining_tokens(quota.tokens_used_on(today))
        return remaining >= FeatureCost.DIAGNOSIS + FeatureCost.DIAGNOSIS_ENRICHMENT

    def enforce_can_add_to_garden(self, quota: Quota, plants_in_garden: int, now: datetime) -> None:
        """`plants_in_garden` = active plants today. Tokens are not checked: identifying already paid."""
        limits = self._limits(quota, now)
        if not limits.can_add_plant(plants_in_garden):
            raise PlantLimitExceededError(
                quota=quota.active_level(now), current_count=plants_in_garden, max_allowed=limits.max_plants,
            )
