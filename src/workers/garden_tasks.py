import structlog

from src.infrastructure.celery_config import celery_app
from src.infrastructure.container import Container
from src.workers.async_runner import run_async

log = structlog.stdlib.get_logger()


@celery_app.task(name="garden.break_missed_streaks")
@run_async
async def break_missed_streaks_task(container: Container | None = None) -> None:
    """Agendada no beat (madrugada, fuso do jardim). Rodar duas vezes no mesmo dia não quebra nada a mais."""
    cnt = container or Container()
    result = await cnt.use_cases.break_streak_cron_use_case().execute()
    log.info("garden.streaks_checked", processed=result.processed, broken=result.broken)
