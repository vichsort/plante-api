from src.shared.domain import PlantEError


class SubscriptionRequiredError(PlantEError):
    """Funcionalidade exclusiva do Plano Pro."""
    code = "PLANTE_4220_SUBSCRIPTION_REQUIRED"
    status_code = 403

    def __init__(self, feature: str):
        super().__init__(
            message=f'"{feature}" is exclusive to the Pro Plan.',
        )


class PlantLimitExceededError(PlantEError):
    """Usuário free atingiu o limite de plantas no jardim."""
    code = "PLANTE_4221_FREE_TIER_PLANT_LIMIT"
    status_code = 403

    def __init__(self, current_count: int, max_allowed: int):
        super().__init__(
            message=f"Limit of {max_allowed} plants reached. Subscribe to the Pro Plan to add more.",
            details={"current_count": current_count, "max_allowed": max_allowed},
        )
