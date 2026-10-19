from datetime import UTC, datetime, timedelta

from src.modules.garden.domain.use_cases.break_missed_streaks import (
    BreakStreakCronUseCase,
)
from src.modules.garden.domain.value_objects.streak import Streak
from src.modules.garden.tests.fakes import (
    CALENDAR,
    FakeGardenUnitOfWork,
    InMemoryUserPlantRepository,
    make_care_schedule,
    make_user_plant,
)
from src.modules.garden.workers.tasks import break_missed_streaks_task
from src.shared.tests.fakes import RecordingPublisher


async def test_task_runs_the_cron() -> None:
    # Arrange: a janela de rega passou inteira
    today = CALENDAR.date_of(datetime.now(UTC))
    plant = make_user_plant(care_schedule=make_care_schedule(next_due_on=today - timedelta(days=2)))
    plant.watering_streak = Streak(current_count=3)
    uow = FakeGardenUnitOfWork(InMemoryUserPlantRepository(plant))

    # Act
    await break_missed_streaks_task(use_case=BreakStreakCronUseCase(uow, RecordingPublisher(), CALENDAR))

    # Assert
    assert plant.watering_streak.current_count == 0
    assert uow.commits == 1
