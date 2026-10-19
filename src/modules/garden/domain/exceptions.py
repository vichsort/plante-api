from uuid import UUID

from src.shared.domain import PlantEError


class PlantNotFoundError(PlantEError):
    """A planta solicitada não existe ou não pertence ao usuário."""
    code = "PLANTE_4530_PLANT_NOT_FOUND"
    status_code = 404

    def __init__(self, plant_id: UUID):
        super().__init__(
            message=f"Plant {plant_id} not found.",
        )


class PlantNotReadyForWateringError(PlantEError):
    """Usuário tentou regar a planta antes do tempo ou no mesmo dia."""
    code = "PLANTE_4540_NOT_READY_FOR_WATERING"
    status_code = 409

    def __init__(self, next_date: str):
        super().__init__(
            message=f"Your plant is well hydrataded! Your next watering date is: {next_date}.",
        )
