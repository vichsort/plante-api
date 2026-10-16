from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.entities.care_schedule import CareSchedule
from src.domain.events.domain_events import StreakBrokenEvent
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.value_objects.local_calendar import LocalCalendar
from src.shared.domain import IDomainPublisher


@dataclass(frozen=True)
class BreakStreakResult:
    processed: int
    broken: int


class BreakStreakCronUseCase:
    """Uma vez por dia (beat): zera a sequência das plantas cuja janela de rega passou inteira."""

    raises = ()

    def __init__(
        self,
        uow: IUnitOfWork,
        publisher: IDomainPublisher,
        calendar: LocalCalendar,
    ) -> None:
        self.uow = uow
        self.publisher = publisher
        self.calendar = calendar

    async def execute(self) -> BreakStreakResult:
        today = self.calendar.date_of(datetime.now(UTC))
        events: list[StreakBrokenEvent] = []
        processed = 0

        async with self.uow as uow:
            due_before = CareSchedule.missed_if_due_before(today)
            for plant in await uow.user_plants.list_with_streak_due_before(due_before):
                processed += 1
                last_count = plant.watering_streak.current_count

                if plant.break_streak_if_missed(today):
                    await uow.user_plants.save(plant)
                    events.append(StreakBrokenEvent.create(
                        user_id=plant.user_id,
                        user_plant_id=plant.id,
                        last_count=last_count,
                    ))
            await uow.commit()

        for event in events:
            await self.publisher.publish(event)

        return BreakStreakResult(processed=processed, broken=len(events))
