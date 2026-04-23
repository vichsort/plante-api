from enum import Enum
import math

class FeatureCost(int, Enum):
    """Mapeia o custo em tokens de cada ação de IA."""
    IDENTIFY = 1
    REIDENTIFY = 1
    DEEP_ANALYSIS = 2
    HEALTH_ANALYSIS = 2

class SubscriptionTier(Enum):
    """
    Define os limites imutáveis de cada plano.
    A tupla representa: (nome, max_plants, max_daily_tokens)
    Usamos math.inf para representar limites infinitos do plano PRO.
    """
    FREE = ("FREE", 3, 3)
    PRO = ("PRO", 50, 30)

    def __init__(self, plan_name: str, max_plants: int | float, max_daily_tokens: int | float):
        self.plan_name = plan_name
        self.max_plants = max_plants
        self.max_daily_tokens = max_daily_tokens

    def can_add_plant(self, current_plant_count: int) -> bool:
        """Verifica se o usuário pode adicionar mais uma planta."""
        return current_plant_count < self.max_plants

    def can_consume(self, feature_cost: FeatureCost, tokens_used_today: int) -> bool:
        """
        Verifica se o usuário tem saldo para a ação.
        Ex: tier.can_consume(FeatureCost.DEEP_ANALYSIS, tokens_used_today=2) -> Retorna False no FREE.
        """
        if tokens_used_today < 0:
            raise ValueError("tokens_used_today cannot be negative.")
        return (tokens_used_today + feature_cost.value) <= self.max_daily_tokens

    def remaining_tokens(self, tokens_used_today: int) -> int | float:
        """Tokens restantes no dia. Retorna inf para PRO."""
        return self.max_daily_tokens - tokens_used_today