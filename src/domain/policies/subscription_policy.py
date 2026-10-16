from datetime import date, datetime

from src.domain.entities.user import User
from src.domain.exceptions import PlantLimitExceededError, SubscriptionRequiredError
from src.domain.value_objects.subscription_tier import FeatureCost


class SubscriptionPolicy:
    """
    Regras do plano. Vale o plano **ativo** (`User.get_active_tier`): PRO vencido conta como FREE.
    A cota de tokens é diária, no dia local (`LocalCalendar`).
    """

    _HEALTH_UNHEALTHY_THRESHOLD = 0.5

    @staticmethod
    def can_spend(user: User, cost: FeatureCost, now: datetime, today: date) -> bool:
        return user.get_active_tier(now).can_consume(cost, user.tokens_used_on(today))

    @staticmethod
    def enforce_can_identify_plant(user: User, now: datetime, today: date) -> None:
        """
        Garante saldo de tokens para uma identificação. O limite do jardim não entra aqui:
        identificar não adiciona planta ao jardim.
        """
        if not SubscriptionPolicy.can_spend(user, FeatureCost.IDENTIFY, now, today):
            raise SubscriptionRequiredError(feature="Mais identificações diárias")

    @staticmethod
    def enforce_can_diagnose(user: User, now: datetime, today: date) -> None:
        """Saldo para o diagnóstico básico (o complemento do Gemini cobra à parte, se couber)."""
        if not SubscriptionPolicy.can_spend(user, FeatureCost.DIAGNOSIS, now, today):
            raise SubscriptionRequiredError(feature="Mais diagnósticos diários")

    @staticmethod
    def can_enrich_diagnosis(user: User, now: datetime, today: date) -> bool:
        """Cabe o diagnóstico mais o complemento do Gemini? Senão, o diagnóstico sai só com o Kindwise."""
        remaining = user.get_active_tier(now).remaining_tokens(user.tokens_used_on(today))
        return remaining >= FeatureCost.DIAGNOSIS + FeatureCost.DIAGNOSIS_ENRICHMENT

    @staticmethod
    def enforce_can_add_to_garden(user: User, plants_in_garden: int, now: datetime) -> None:
        """
        Garante que o usuário pode adicionar uma planta ao jardim (`plants_in_garden` = plantas
        ativas hoje). Tokens não são verificados aqui — já foram consumidos na identificação.
        """
        tier = user.get_active_tier(now)
        if not tier.can_add_plant(plants_in_garden):
            raise PlantLimitExceededError(limit=tier.max_plants)

    @staticmethod
    def health_unhealthy_threshold() -> float:
        return SubscriptionPolicy._HEALTH_UNHEALTHY_THRESHOLD
