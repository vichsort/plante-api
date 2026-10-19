import structlog

from src.bootstrap.celery_config import celery_app
from src.bootstrap.connections import task_container
from src.bootstrap.container import Container
from src.shared.workers import run_async

log = structlog.stdlib.get_logger()


@celery_app.task(name="garden.break_missed_streaks")
@run_async
async def break_missed_streaks_task(container: Container | None = None) -> None:
    """Agendada no beat (madrugada, fuso local). Rodar duas vezes no mesmo dia não quebra nada a mais."""
    async with task_container(container) as cnt:
        result = await cnt.use_cases.break_streak_cron_use_case().execute()
    log.info("garden.streaks_checked", processed=result.processed, broken=result.broken)
