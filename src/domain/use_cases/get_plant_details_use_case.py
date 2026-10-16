from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.entities.plant_species import PlantSpecies
from src.domain.entities.user_plant import UserPlant
from src.domain.exceptions import PlantNotFoundError
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import UserPlantId
from src.domain.value_objects.local_calendar import LocalCalendar
from src.shared.domain import UserId


@dataclass(frozen=True)
class GetPlantDetailsInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId


@dataclass(frozen=True)
class PlantDetailsOutput:
    plant: UserPlant
    species: PlantSpecies | None
    needs_watering: bool


class GetPlantDetailsUseCase:
    raises = (PlantNotFoundError,)

    def __init__(self, uow: IUnitOfWork, calendar: LocalCalendar) -> None:
        self.uow = uow
        self.calendar = calendar

    async def execute(self, dto: GetPlantDetailsInputDTO) -> PlantDetailsOutput:
        async with self.uow as uow:
            details = await uow.user_plants.get_details(dto.user_plant_id, dto.user_id)

        if details is None:
            raise PlantNotFoundError(dto.user_plant_id)

        today = self.calendar.date_of(datetime.now(UTC))
        return PlantDetailsOutput(
            plant=details.plant,
            species=details.species,
            needs_watering=details.plant.needs_watering(today),
        )
