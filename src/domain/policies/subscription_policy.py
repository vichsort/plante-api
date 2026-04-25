from src.domain.entities.user import User
from src.domain.value_objects.subscription_tier import FeatureCost
from src.domain.exceptions import PlantLimitExceededError, SubscriptionRequiredError

class SubscriptionPolicy:
    """
    Política de domínio responsável por aplicar as regras de negócio
    vinculadas ao plano de assinatura do usuário.
    """

    _HEALTH_UNHEALTHY_THRESHOLD = 0.5

    @staticmethod
    def enforce_can_identify_plant(user: User) -> None:
        """
        Garante que o usuário pode identificar e adicionar uma nova planta.
        Avalia tanto o limite do jardim quanto o saldo de tokens diários.
        """
        # Verifica limite de plantas no jardim (apenas Free tem limite)
        if not user.subscription_tier.can_add_plant(user.garden_count):
            raise PlantLimitExceededError(limit=user.subscription_tier.max_plants)

        # Verifica se tem tokens suficientes para a identificação
        if not user.subscription_tier.can_consume(FeatureCost.IDENTIFY, user.tokens_used_today):
            raise SubscriptionRequiredError(feature="Mais identificações diárias")

    @staticmethod
    def enforce_can_deep_analyze(user: User) -> None:
        """
        Garante que o usuário tem saldo/plano para uma análise profunda.
        """
        if not user.subscription_tier.can_consume(FeatureCost.DEEP_ANALYSIS, user.tokens_used_today):
            raise SubscriptionRequiredError(feature="Análise Profunda com IA")

    @staticmethod
    def enforce_can_add_to_garden(user: User) -> None:
        """
        Garante que o usuário pode adicionar uma planta ao jardim.
        Tokens não são verificados aqui — já foram consumidos na identificação.
        """
        if not user.subscription_tier.can_add_plant(user.garden_count):
            raise PlantLimitExceededError(limit=user.subscription_tier.max_plants)

    @staticmethod
    def health_unhealthy_threshold() -> float:
        return SubscriptionPolicy._HEALTH_UNHEALTHY_THRESHOLD