from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.events.domain_events import StreakBrokenEvent
from src.domain.ports.domain_publisher import IDomainPublisher
from src.domain.ports.unit_of_work import IUnitOfWork


@dataclass(frozen=True)
class BreakStreakResult:
    processed: int
    broken: int


class BreakStreakCronUseCase:
    raises = ()

    def __init__(
        self,
        uow: IUnitOfWork,
        publisher: IDomainPublisher,
    ) -> None:
        self.uow = uow
        self.publisher = publisher

    async def execute(self) -> BreakStreakResult:
        now = datetime.now(UTC)
        events: list[StreakBrokenEvent] = []
        processed = 0

        async with self.uow as uow:
            for plant in await uow.user_plants.get_overdue_plants(now):
                processed += 1
                old_streak = plant.watering_streak.current_count

                if plant.check_and_reset_streak(now):
                    await uow.user_plants.save(plant)
                    events.append(StreakBrokenEvent.create(
                        user_id=plant.user_id,
                        user_plant_id=plant.id,
                        last_count=old_streak,
                    ))
            await uow.commit()

        for event in events:
            await self.publisher.publish(event)

        return BreakStreakResult(processed=processed, broken=len(events))
