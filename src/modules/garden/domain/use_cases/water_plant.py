from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.garden.domain.entities.user_plant import UserPlant
from src.modules.garden.domain.events import PlantWateredEvent
from src.modules.garden.domain.exceptions import (
    PlantNotFoundError,
    PlantNotReadyForWateringError,
)
from src.modules.garden.domain.ports.unit_of_work import IGardenUnitOfWork
from src.modules.garden.domain.value_objects.ids import UserPlantId
from src.shared.domain import IDomainPublisher, LocalCalendar, UserId


@dataclass(frozen=True)
class WaterPlantInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId

class WaterPlantUseCase:
    raises = (PlantNotFoundError, PlantNotReadyForWateringError)

    def __init__(
        self,
        uow: IGardenUnitOfWork,
        publisher: IDomainPublisher,
        calendar: LocalCalendar,
    ) -> None:
        self.uow = uow
        self.publisher = publisher
        self.calendar = calendar

    async def execute(self, dto: WaterPlantInputDTO) -> UserPlant:
        async with self.uow as uow:
            plant = await uow.user_plants.get_by_id(dto.user_plant_id, dto.user_id)
            if not plant:
                raise PlantNotFoundError(dto.user_plant_id)

            plant.water(datetime.now(UTC), self.calendar)
            await uow.user_plants.save(plant)
            await uow.commit()

        await self.publisher.publish(PlantWateredEvent.create(
            user_id=dto.user_id,
            user_plant_id=plant.id,
            current_streak=plant.watering_streak.current_count,
        ))

        return plant
