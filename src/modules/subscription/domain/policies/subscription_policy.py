from datetime import date, datetime

from src.modules.subscription.domain.entities.subscription import Subscription
from src.modules.subscription.domain.exceptions import (
    PlantLimitExceededError,
    SubscriptionRequiredError,
)
from src.modules.subscription.domain.value_objects.tier import FeatureCost


class SubscriptionPolicy:
    """
    Regras do plano. Vale o plano **ativo** (`Subscription.active_tier`): PRO vencido conta como
    FREE. A cota de tokens é diária, no dia local (`LocalCalendar`).
    """

    @staticmethod
    def can_spend(subscription: Subscription, cost: FeatureCost, now: datetime, today: date) -> bool:
        return subscription.active_tier(now).can_consume(cost, subscription.tokens_used_on(today))

    @staticmethod
    def enforce_can_identify_plant(subscription: Subscription, now: datetime, today: date) -> None:
        """Saldo para uma identificação. O limite do jardim não entra aqui: identificar não adiciona planta."""
        if not SubscriptionPolicy.can_spend(subscription, FeatureCost.IDENTIFY, now, today):
            raise SubscriptionRequiredError(feature="Mais identificações diárias")

    @staticmethod
    def enforce_can_diagnose(subscription: Subscription, now: datetime, today: date) -> None:
        """Saldo para o diagnóstico básico (o complemento do Gemini cobra à parte, se couber)."""
        if not SubscriptionPolicy.can_spend(subscription, FeatureCost.DIAGNOSIS, now, today):
            raise SubscriptionRequiredError(feature="Mais diagnósticos diários")

    @staticmethod
    def can_enrich_diagnosis(subscription: Subscription, now: datetime, today: date) -> bool:
        """Cabe o diagnóstico mais o complemento do Gemini? Senão, o diagnóstico sai só com o Kindwise."""
        remaining = subscription.active_tier(now).remaining_tokens(subscription.tokens_used_on(today))
        return remaining >= FeatureCost.DIAGNOSIS + FeatureCost.DIAGNOSIS_ENRICHMENT

    @staticmethod
    def enforce_can_add_to_garden(subscription: Subscription, plants_in_garden: int, now: datetime) -> None:
        """`plants_in_garden` = plantas ativas hoje. Tokens não entram: já foram cobrados na identificação."""
        tier = subscription.active_tier(now)
        if not tier.can_add_plant(plants_in_garden):
            raise PlantLimitExceededError(current_count=plants_in_garden, max_allowed=tier.max_plants)
