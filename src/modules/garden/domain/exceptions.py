from datetime import date
from uuid import UUID

from src.shared.domain import PlantEError


class PlantNotFoundError(PlantEError):
    """The plant does not exist or belongs to another user."""
    code = "PLANTE_4530_PLANT_NOT_FOUND"
    status_code = 404

    def __init__(self, plant_id: UUID):
        super().__init__(
            message=f"Plant {plant_id} not found.",
        )


class PlantNotReadyForWateringError(PlantEError):
    """The plant was watered before its watering window opened."""
    code = "PLANTE_4540_NOT_READY_FOR_WATERING"
    status_code = 409

    def __init__(self, next_date: date):
        super().__init__(
            message=f"Your plant is well hydrated! Next watering on {next_date.isoformat()}.",
            details={"next_watering_on": next_date.isoformat()},
        )
