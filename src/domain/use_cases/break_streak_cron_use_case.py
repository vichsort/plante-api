from datetime import UTC, datetime
from typing import Any

from src.domain.events.domain_events import StreakBrokenEvent
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.user_plant_repository import IUserPlantRepository


class BreakStreakCronUseCase:
    raises = ()

    def __init__(
        self,
        user_plant_repo: IUserPlantRepository,
        publisher: IDomainPublisher
    ):
        self.user_plant_repo = user_plant_repo
        self.publisher = publisher

    async def execute(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        
        overdue_plants = await self.user_plant_repo.get_overdue_plants(now)
        
        counts = {"processed": 0, "broken": 0}

        for plant in overdue_plants:
            counts["processed"] += 1
            
            old_streak = plant.watering_streak.current_count
            
            if plant.check_and_reset_streak(now):
                counts["broken"] += 1
                await self.user_plant_repo.save(plant)
                
                event = StreakBrokenEvent.create(
                    user_id=plant.user_id,
                    user_plant_id=plant.id,
                    last_count=old_streak
                )
                await self.publisher.publish(event)

        return counts