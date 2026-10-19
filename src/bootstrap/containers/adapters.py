from dependency_injector import containers, providers

from src.bootstrap.celery_config import celery_app
from src.bootstrap.settings import Settings
from src.modules.identity.workers import route_event as identity_events
from src.shared.adapters import (
    CeleryPublisher,
    CircuitBreaker,
    KindwiseClient,
    PillowImageSanitizer,
    RedisClient,
    S3ImageStorage,
)


class AdaptersContainer(containers.DeclarativeContainer):
    settings: providers.Dependency[Settings] = providers.Dependency()

    image_sanitizer = providers.Singleton(PillowImageSanitizer)
    # Cada módulo com tasks entrega a rota dos próprios eventos
    domain_publisher = providers.Singleton(CeleryPublisher, celery_app=celery_app, routes=[identity_events])

    redis = providers.Singleton(
        RedisClient.from_url,
        url=settings.provided.redis_url,
        socket_timeout=settings.provided.redis_socket_timeout_seconds,
        socket_connect_timeout=settings.provided.redis_connect_timeout_seconds,
    )

    image_storage = providers.Singleton(
        S3ImageStorage,
        bucket_name=settings.provided.s3_bucket,
        region=settings.provided.aws_region,
        aws_access_key_id=settings.provided.aws_access_key_id,
        aws_secret_access_key=settings.provided.aws_secret_access_key,
    )

    # Kindwise atende identificação e saúde: um único breaker por provedor
    kindwise_breaker = providers.Singleton(
        CircuitBreaker,
        name="Kindwise",
        failure_threshold=settings.provided.ai_breaker_failure_threshold,
        recovery_timeout_seconds=settings.provided.ai_breaker_recovery_timeout_seconds,
    )
    plantnet_breaker = providers.Singleton(
        CircuitBreaker,
        name="PlantNet",
        failure_threshold=settings.provided.ai_breaker_failure_threshold,
        recovery_timeout_seconds=settings.provided.ai_breaker_recovery_timeout_seconds,
    )

    # Kindwise atende identificação e saúde: um cliente só, cada módulo com o próprio adapter
    kindwise_client = providers.Singleton(
        KindwiseClient,
        api_key=settings.provided.kindwise_key,
    )