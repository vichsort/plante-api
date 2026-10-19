from enum import Enum, IntEnum


class FeatureCost(IntEnum):
    """Custo em tokens de cada ação de IA."""
    IDENTIFY = 1
    DEEP_ANALYSIS = 2
    DIAGNOSIS = 1             # diagnóstico do Kindwise
    DIAGNOSIS_ENRICHMENT = 1  # complemento do Gemini, só quando entregue


class SubscriptionTier(Enum):
    """Limites de cada plano: (nome, plantas no jardim, tokens por dia)."""
    FREE = ("FREE", 3, 3)
    PRO = ("PRO", 50, 30)

    def __init__(self, plan_name: str, max_plants: int, max_daily_tokens: int):
        self.plan_name = plan_name
        self.max_plants = max_plants
        self.max_daily_tokens = max_daily_tokens

    def can_add_plant(self, current_plant_count: int) -> bool:
        return current_plant_count < self.max_plants

    def can_consume(self, feature_cost: FeatureCost, tokens_used_today: int) -> bool:
        if tokens_used_today < 0:
            raise ValueError("tokens_used_today cannot be negative.")
        return (tokens_used_today + feature_cost.value) <= self.max_daily_tokens

    def remaining_tokens(self, tokens_used_today: int) -> int:
        return self.max_daily_tokens - tokens_used_today
