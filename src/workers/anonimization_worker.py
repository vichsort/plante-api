from celery import shared_task
from datetime import datetime, timezone, timedelta
from structlog import get_logger

logger = get_logger()

RETENTION_DAYS = 30

@shared_task(
    name="workers.anonymize_confirmed_samples",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    acks_late=True,
)
def anonymize_confirmed_samples() -> dict:
    """
    Anonimiza samples confirmadas há mais de RETENTION_DAYS dias.
    Idempotente: rodar duas vezes não causa efeito colateral.
    """
    from src.infrastructure.container import get_sample_repository

    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    sample_repo = get_sample_repository()

    import asyncio
    samples = asyncio.run(sample_repo.get_confirmed_before(cutoff=cutoff))

    anonymized = 0
    failed = 0

    for sample in samples:
        try:
            if sample.user_id is None:
                continue  # já anonimizado
            updated = sample.anonymize()
            asyncio.run(sample_repo.save(updated))
            anonymized += 1
        except Exception as e:
            logger.error("anonymization_failed", sample_id=sample.id, error=str(e))
            failed += 1

    logger.info("anonymization_done", anonymized=anonymized, failed=failed)
    return {"anonymized": anonymized, "failed": failed}