from src.domain.entities.user import User
from src.domain.exceptions import PlantLimitExceededError, SubscriptionRequiredError
from src.domain.value_objects.subscription_tier import FeatureCost


class SubscriptionPolicy:
    """
    Política de domínio responsável por aplicar as regras de negócio
    vinculadas ao plano de assinatura do usuário.
    """

    _HEALTH_UNHEALTHY_THRESHOLD = 0.5

    @staticmethod
    def enforce_can_identify_plant(user: User) -> None:
        """
        Garante saldo de tokens para uma identificação. O limite do jardim não entra aqui:
        identificar não adiciona planta ao jardim.
        """
        if not user.subscription.can_consume(FeatureCost.IDENTIFY, user.tokens_used_today):
            raise SubscriptionRequiredError(feature="Mais identificações diárias")

    @staticmethod
    def enforce_can_deep_analyze(user: User) -> None:
        """
        Garante que o usuário tem saldo/plano para uma análise profunda.
        """
        if not user.subscription.can_consume(FeatureCost.DEEP_ANALYSIS, user.tokens_used_today):
            raise SubscriptionRequiredError(feature="Análise Profunda com IA")

    @staticmethod
    def enforce_can_add_to_garden(user: User, plants_in_garden: int) -> None:
        """
        Garante que o usuário pode adicionar uma planta ao jardim (`plants_in_garden` = plantas
        ativas hoje). Tokens não são verificados aqui — já foram consumidos na identificação.
        """
        if not user.subscription.can_add_plant(plants_in_garden):
            raise PlantLimitExceededError(limit=user.subscription.max_plants)

    @staticmethod
    def health_unhealthy_threshold() -> float:
        return SubscriptionPolicy._HEALTH_UNHEALTHY_THRESHOLD