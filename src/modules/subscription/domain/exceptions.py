from src.shared.domain import PlantEError


class SubscriptionRequiredError(PlantEError):
    """Funcionalidade exclusiva do Plano Pro."""
    code = "PLANTE_4019_SUBSCRIPTION_REQUIRED"
    status_code = 403

    def __init__(self, feature: str):
        super().__init__(
            message=f'"{feature}" is exclusive to the Pro Plan (R$ 6,99/month).',
        )


class PlantLimitExceededError(PlantEError):
    """Usuário free atingiu o limite de plantas no jardim."""
    code = "PLANTE_4005_FREE_TIER_PLANT_LIMIT"
    status_code = 403

    def __init__(self, limit: int):
        super().__init__(
            message=f"Limit of {limit} plants reached. Subscribe to the Pro Plan to add more.",
            details={"current_count": str(limit), "max_allowed": str(limit)},
        )
