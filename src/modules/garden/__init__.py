"""
garden: as plantas que o usuário cultiva, a rega e a sequência (README.md). A API pública é só
domínio; a composição monta o módulo por `src.modules.garden.container`, `.api` e `.workers`.
"""
from src.modules.garden.domain.entities.user_plant import UserPlant
from src.modules.garden.domain.events import (
    PlantAddedToGardenEvent,
    PlantWateredEvent,
    StreakBrokenEvent,
)
from src.modules.garden.domain.exceptions import PlantNotFoundError
from src.modules.garden.domain.services.plant_lookup import IPlantLookup
from src.modules.garden.domain.value_objects.ids import UserPlantId

__all__ = [
    "IPlantLookup",
    "PlantAddedToGardenEvent",
    "PlantNotFoundError",
    "PlantWateredEvent",
    "StreakBrokenEvent",
    "UserPlant",
    "UserPlantId",
]
