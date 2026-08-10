from datetime import UTC, datetime, timedelta

from celery import shared_task
from structlog import get_logger

from src.infrastructure.container import Container
from src.workers.async_runner import run_async

logger = get_logger()
RETENTION_DAYS = 30

@shared_task(
    name="workers.anonymize_confirmed_samples",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    acks_late=True,
)
@run_async
async def anonymize_confirmed_samples(container: Container | None = None) -> dict:
    """
    Anonimiza samples confirmadas há mais de RETENTION_DAYS dias.
    Idempotente: rodar duas vezes não causa efeito colateral.
    """
    cnt = container or Container()
    sample_repo = cnt.repositories.identification_sample_repository()

    cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
    samples = await sample_repo.get_confirmed_before(cutoff=cutoff)

    anonymized = 0
    failed = 0

    for sample in samples:
        try:
            if sample.user_id is None:
                continue
            updated = sample.anonymize()
            await sample_repo.save(updated)
            anonymized += 1
        except Exception as e:
            logger.error("anonymization_failed", sample_id=str(sample.id), error=str(e))
            failed += 1

    logger.info("anonymization_done", anonymized=anonymized, failed=failed)
    return {"anonymized": anonymized, "failed": failed}