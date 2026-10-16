from unittest.mock import AsyncMock

import pytest
from celery.schedules import crontab

from src.bootstrap.celery_config import celery_app
from src.bootstrap.container import Container
from src.domain.use_cases.break_streak_cron_use_case import BreakStreakResult
from src.workers.garden_tasks import break_missed_streaks_task


def test_streak_check_is_scheduled_daily_in_the_garden_time_zone() -> None:
    # Arrange
    schedule = {entry["task"]: entry["schedule"] for entry in celery_app.conf.beat_schedule.values()}

    # Act
    entry = schedule.get("garden.break_missed_streaks")

    # Assert: antes o beat_schedule era vazio e a sequência nunca quebrava
    assert entry == crontab(hour=3, minute=0)
    assert celery_app.conf.timezone == "America/Sao_Paulo"


@pytest.mark.asyncio
async def test_task_runs_the_cron_use_case() -> None:
    # Arrange
    use_case = AsyncMock()
    use_case.execute.return_value = BreakStreakResult(processed=2, broken=1)
    container = Container()

    # Act
    with container.use_cases.break_streak_cron_use_case.override(use_case):
        await break_missed_streaks_task(container=container)

    # Assert
    use_case.execute.assert_awaited_once()
