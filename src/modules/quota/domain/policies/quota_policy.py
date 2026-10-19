from datetime import date, datetime

from src.modules.quota.domain.entities.quota import Quota
from src.modules.quota.domain.exceptions import (
    DailyQuotaExceededError,
    PlantLimitExceededError,
)
from src.modules.quota.domain.value_objects.tier import FeatureCost


class QuotaPolicy:
    """
    Regras do plano. Vale o plano **ativo** (`Quota.active_tier`): PRO vencido conta como
    FREE. A cota de tokens é diária, no dia local (`LocalCalendar`).
    """

    @staticmethod
    def can_spend(quota: Quota, cost: FeatureCost, now: datetime, today: date) -> bool:
        return quota.active_tier(now).can_consume(cost, quota.tokens_used_on(today))

    @staticmethod
    def _enforce_can_spend(quota: Quota, cost: FeatureCost, now: datetime, today: date) -> None:
        if not QuotaPolicy.can_spend(quota, cost, now, today):
            tier = quota.active_tier(now)
            raise DailyQuotaExceededError(
                plan=tier.plan_name,
                used_today=quota.tokens_used_on(today),
                daily_limit=tier.max_daily_tokens,
            )

    @staticmethod
    def enforce_can_identify_plant(quota: Quota, now: datetime, today: date) -> None:
        """Saldo para uma identificação. O limite do jardim não entra aqui: identificar não adiciona planta."""
        QuotaPolicy._enforce_can_spend(quota, FeatureCost.IDENTIFY, now, today)

    @staticmethod
    def enforce_can_diagnose(quota: Quota, now: datetime, today: date) -> None:
        """Saldo para o diagnóstico básico (o complemento do Gemini cobra à parte, se couber)."""
        QuotaPolicy._enforce_can_spend(quota, FeatureCost.DIAGNOSIS, now, today)

    @staticmethod
    def can_enrich_diagnosis(quota: Quota, now: datetime, today: date) -> bool:
        """Cabe o diagnóstico mais o complemento do Gemini? Senão, o diagnóstico sai só com o Kindwise."""
        remaining = quota.active_tier(now).remaining_tokens(quota.tokens_used_on(today))
        return remaining >= FeatureCost.DIAGNOSIS + FeatureCost.DIAGNOSIS_ENRICHMENT

    @staticmethod
    def enforce_can_add_to_garden(quota: Quota, plants_in_garden: int, now: datetime) -> None:
        """`plants_in_garden` = plantas ativas hoje. Tokens não entram: já foram cobrados na identificação."""
        tier = quota.active_tier(now)
        if not tier.can_add_plant(plants_in_garden):
            raise PlantLimitExceededError(
                plan=tier.plan_name, current_count=plants_in_garden, max_allowed=tier.max_plants,
            )
