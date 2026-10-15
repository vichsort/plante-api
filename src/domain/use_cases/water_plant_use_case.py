from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.entities.user_plant import UserPlant
from src.domain.events.domain_events import PlantWateredEvent
from src.domain.exceptions import (
    ForbiddenError,
    PlantNotFoundError,
    PlantNotReadyForWateringError,
)
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.domain.value_objects.ids import UserId, UserPlantId


@dataclass(frozen=True)
class WaterPlantInputDTO:
    user_id: UserId
    user_plant_id: UserPlantId

class WaterPlantUseCase:
    raises = (ForbiddenError, PlantNotFoundError, PlantNotReadyForWateringError)

    def __init__(
        self,
        user_plant_repo: IUserPlantRepository,
        publisher: IDomainPublisher,
    ) -> None:
        self.user_plant_repo = user_plant_repo
        self.publisher = publisher

    async def execute(self, dto: WaterPlantInputDTO) -> UserPlant:
        plant = await self.user_plant_repo.get_by_id(dto.user_plant_id, dto.user_id)
        if not plant:
            raise PlantNotFoundError(dto.user_plant_id)

        if plant.user_id != dto.user_id:
            raise ForbiddenError("Você não tem permissão para regar esta planta.")

        now_utc = datetime.now(UTC)
        plant.water(now_utc)

        await self.user_plant_repo.save(plant)

        event = PlantWateredEvent.create(
            user_id=dto.user_id,
            user_plant_id=plant.id,
            current_streak=plant.watering_streak.current_count,
        )
        await self.publisher.publish(event)

        return plant
