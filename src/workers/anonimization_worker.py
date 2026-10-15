from datetime import UTC, datetime, timedelta

import structlog
from celery import shared_task

from src.infrastructure.container import Container
from src.workers.async_runner import run_async

logger = structlog.stdlib.get_logger()
RETENTION_DAYS = 30

@shared_task(
    name="workers.anonymize_confirmed_samples",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    acks_late=True,
)
@run_async
async def anonymize_confirmed_samples(container: Container | None = None) -> dict[str, int]:
    """
    Anonimiza samples confirmadas há mais de RETENTION_DAYS dias.
    Idempotente: rodar duas vezes não causa efeito colateral.
    """
    cnt = container or Container()
    cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)

    anonymized = 0
    failed = 0

    async with cnt.infra.unit_of_work() as uow:
        for sample in await uow.identification_samples.get_confirmed_before(cutoff=cutoff):
            if sample.user_id is None:
                continue
            try:
                await uow.identification_samples.save(sample.anonymize())
                anonymized += 1
            except Exception as e:
                logger.error("anonymization_failed", sample_id=str(sample.id), error=str(e))
                failed += 1
        await uow.commit()

    logger.info("anonymization_done", anonymized=anonymized, failed=failed)
    return {"anonymized": anonymized, "failed": failed}
