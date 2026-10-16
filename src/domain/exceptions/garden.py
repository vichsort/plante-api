from uuid import UUID

from src.shared.domain import PlantEError


class PlantNotFoundError(PlantEError):
    """A planta solicitada não existe ou não pertence ao usuário."""
    code = "PLANTE_4001_PLANT_NOT_FOUND"
    status_code = 404

    def __init__(self, plant_id: UUID):
        super().__init__(
            message=f"Plant {plant_id} not found.",
        )


class PlantLimitExceededError(PlantEError):
    """Usuário free atingiu o limite de plantas no jardim."""
    code = "PLANTE_4005_FREE_TIER_PLANT_LIMIT"
    status_code = 403

    def __init__(self, limit: int | float):
        super().__init__(
            message=f"Limit of {limit} plants reached. Subscribe to the Pro Plan to add more.",
            details={"current_count": str(limit), "max_allowed": str(limit)},
        )


class PlantNotReadyForWateringError(PlantEError):
    """Usuário tentou regar a planta antes do tempo ou no mesmo dia."""
    code = "PLANTE_4016_NOT_READY_FOR_WATERING"
    status_code = 400

    def __init__(self, next_date: str):
        super().__init__(
            message=f"Your plant is well hydrataded! Your next watering date is: {next_date}.",
        )
