from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.domain.events.domain_events import PlantWateredEvent
from src.domain.exceptions import ForbiddenError, PlantNotFoundError
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.user_plant_repository import IUserPlantRepository


@dataclass(frozen=True)
class WaterPlantInputDTO:
    user_id: Any
    user_plant_id: Any

class WaterPlantUseCase:
    def __init__(
        self,
        user_plant_repo: IUserPlantRepository,
        publisher: IDomainPublisher
    ):
        self.user_plant_repo = user_plant_repo
        self.publisher = publisher

    async def execute(self, dto: WaterPlantInputDTO) -> dict:
        plant = await self.user_plant_repo.get_by_id(dto.user_plant_id, dto.user_id)
        if not plant:
            raise PlantNotFoundError(dto.user_plant_id)

        if str(plant.user_id) != str(dto.user_id):
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

        return {
            "user_plant_id": plant.id,
            "last_watered_at": plant.last_watered_at.isoformat() if plant.last_watered_at else None,
            "next_due_at": plant.care_schedule.next_due_at.isoformat() if plant.care_schedule.next_due_at else None,
            "current_streak": plant.watering_streak.current_count,
        }