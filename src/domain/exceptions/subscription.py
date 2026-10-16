from src.shared.domain import PlantEError


class SubscriptionRequiredError(PlantEError):
    """Funcionalidade exclusiva do Plano Pro."""
    code = "PLANTE_4019_SUBSCRIPTION_REQUIRED"
    status_code = 403

    def __init__(self, feature: str):
        super().__init__(
            message=f'"{feature}" is exclusive to the Pro Plan (R$ 6,99/month).',
        )
