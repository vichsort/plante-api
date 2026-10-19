import structlog
from celery import shared_task
from dependency_injector.wiring import Provide, inject

from src.modules.garden.container import GardenContainer
from src.modules.garden.domain.use_cases.break_missed_streaks import (
    BreakStreakCronUseCase,
)
from src.shared.workers import run_async

log = structlog.stdlib.get_logger()
BREAK_MISSED_STREAKS_TASK = "garden.break_missed_streaks"


@shared_task(name=BREAK_MISSED_STREAKS_TASK)
@run_async
@inject
async def break_missed_streaks_task(
    use_case: BreakStreakCronUseCase = Provide[GardenContainer.break_missed_streaks_use_case],
) -> None:
    """Agendada no beat (madrugada, fuso local). Rodar duas vezes no mesmo dia não quebra nada a mais."""
    result = await use_case.execute()
    log.info("garden.streaks_checked", processed=result.processed, broken=result.broken)
