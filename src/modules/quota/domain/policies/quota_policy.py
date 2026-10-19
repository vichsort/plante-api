from datetime import date, datetime

from src.modules.quota.domain.entities.quota import Quota
from src.modules.quota.domain.exceptions import (
    DailyQuotaExceededError,
    PlantLimitExceededError,
)
from src.modules.quota.domain.value_objects.level import (
    DEFAULT_LIMITS,
    FeatureCost,
    QuotaLimits,
)


class QuotaPolicy:
    """
    Quota rules. The **active** level counts (`Quota.active_level`): an expired extended quota is
    standard. The token quota is daily, on the local day (`LocalCalendar`).
    """

    @staticmethod
    def _limits(quota: Quota, now: datetime) -> QuotaLimits:
        return DEFAULT_LIMITS.of(quota.active_level(now))

    @staticmethod
    def can_spend(quota: Quota, cost: FeatureCost, now: datetime, today: date) -> bool:
        return QuotaPolicy._limits(quota, now).can_consume(cost, quota.tokens_used_on(today))

    @staticmethod
    def _enforce_can_spend(quota: Quota, cost: FeatureCost, now: datetime, today: date) -> None:
        if not QuotaPolicy.can_spend(quota, cost, now, today):
            raise DailyQuotaExceededError(
                quota=quota.active_level(now),
                used_today=quota.tokens_used_on(today),
                daily_limit=QuotaPolicy._limits(quota, now).daily_tokens,
            )

    @staticmethod
    def enforce_can_identify_plant(quota: Quota, now: datetime, today: date) -> None:
        """Tokens for one identification. The garden limit is not checked: identifying adds no plant."""
        QuotaPolicy._enforce_can_spend(quota, FeatureCost.IDENTIFY, now, today)

    @staticmethod
    def enforce_can_diagnose(quota: Quota, now: datetime, today: date) -> None:
        """Tokens for the basic diagnosis (the Gemini add-on is charged apart, if it fits)."""
        QuotaPolicy._enforce_can_spend(quota, FeatureCost.DIAGNOSIS, now, today)

    @staticmethod
    def can_enrich_diagnosis(quota: Quota, now: datetime, today: date) -> bool:
        """Do the diagnosis and the Gemini add-on both fit? If not, the diagnosis is Kindwise only."""
        remaining = QuotaPolicy._limits(quota, now).remaining_tokens(quota.tokens_used_on(today))
        return remaining >= FeatureCost.DIAGNOSIS + FeatureCost.DIAGNOSIS_ENRICHMENT

    @staticmethod
    def enforce_can_add_to_garden(quota: Quota, plants_in_garden: int, now: datetime) -> None:
        """`plants_in_garden` = active plants today. Tokens are not checked: identifying already paid."""
        limits = QuotaPolicy._limits(quota, now)
        if not limits.can_add_plant(plants_in_garden):
            raise PlantLimitExceededError(
                quota=quota.active_level(now), current_count=plants_in_garden, max_allowed=limits.max_plants,
            )
