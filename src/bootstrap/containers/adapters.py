from dependency_injector import containers, providers

from src.adapters.ai.consensus.consensus_adapter import ConsensusIdentifier
from src.adapters.ai.gemini.gemini_adapter import GeminiHealthEnricher
from src.adapters.ai.kindwise.kindwise_adapter import KindwiseAdapter
from src.adapters.ai.plantnet.plantnet_adapter import PlantNetAdapter
from src.adapters.resilience import (
    CircuitBreakerHealthAnalyzer,
    CircuitBreakerPlantIdentifier,
)
from src.bootstrap.celery_config import celery_app
from src.bootstrap.settings import Settings
from src.modules.identity.workers import route_event as identity_events
from src.shared.adapters import (
    CeleryPublisher,
    CircuitBreaker,
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

    kindwise_adapter = providers.Singleton(
        KindwiseAdapter,
        api_key=settings.provided.plant_id_api_key,
    )

    plantnet_adapter = providers.Singleton(
        PlantNetAdapter,
        api_key=settings.provided.plantnet_api_key,
    )

    kindwise_identifier = providers.Singleton(
        CircuitBreakerPlantIdentifier,
        inner=kindwise_adapter,
        breaker=kindwise_breaker,
    )

    plantnet_identifier = providers.Singleton(
        CircuitBreakerPlantIdentifier,
        inner=plantnet_adapter,
        breaker=plantnet_breaker,
    )

    consensus_identifier = providers.Singleton(
        ConsensusIdentifier,
        kindwise=kindwise_identifier,
        plantnet=plantnet_identifier,
    )

    # Selector compara pela string do valor: o bool precisa virar "true"/"false"
    plant_identifier = providers.Selector(
        providers.Callable(lambda enabled: "true" if enabled else "false", settings.provided.consensus_enabled),
        true=consensus_identifier,
        false=kindwise_identifier,
    )

    health_analyzer = providers.Singleton(
        CircuitBreakerHealthAnalyzer,
        inner=kindwise_adapter,
        breaker=kindwise_breaker,
    )

    health_enricher = providers.Singleton(
        GeminiHealthEnricher,
        api_key=settings.provided.gemini_api_key,
    )