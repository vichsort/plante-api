from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.catalog import ISpeciesRegistry, PlantSpecies
from src.modules.garden.domain.entities.user_plant import UserPlant
from src.modules.garden.domain.exceptions import PlantNotFoundError
from src.modules.garden.domain.ports.unit_of_work import IGardenUnitOfWork
from src.modules.garden.domain.value_objects.ids import UserPlantId
from src.shared.domain import IImageStorage, LocalCalendar, UserId


@dataclass(frozen=True)
class GetPlantDetailsInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId


@dataclass(frozen=True)
class PlantDetailsOutput:
    plant: UserPlant
    species: PlantSpecies | None
    needs_watering: bool
    image_url: str | None


class GetPlantDetailsUseCase:
    raises = (PlantNotFoundError,)

    def __init__(
        self, uow: IGardenUnitOfWork, calendar: LocalCalendar, catalog: ISpeciesRegistry, storage: IImageStorage,
    ) -> None:
        self.uow = uow
        self.calendar = calendar
        self.catalog = catalog
        self.storage = storage

    async def execute(self, dto: GetPlantDetailsInputDTO) -> PlantDetailsOutput:
        async with self.uow as uow:
            plant = await uow.user_plants.get_by_id(dto.user_plant_id, dto.user_id)
            if plant is None:
                raise PlantNotFoundError(dto.user_plant_id)
            # A espécie é do catalog: pergunta pelo service, não por JOIN na tabela dele
            species = await self.catalog.find_by_name(plant.scientific_name)

        today = self.calendar.date_of(datetime.now(UTC))
        image_url = await self.storage.signed_url(plant.primary_image_key) if plant.primary_image_key else None
        return PlantDetailsOutput(
            plant=plant, species=species, needs_watering=plant.needs_watering(today), image_url=image_url,
        )
