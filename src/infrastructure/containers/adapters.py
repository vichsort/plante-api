import httpx
from dependency_injector import containers, providers
from redis.asyncio import Redis

from src.adapters.ai.consensus.consensus_adapter import ConsensusIdentifier
from src.adapters.ai.gemini.gemini_adapter import GeminiAdapter
from src.adapters.ai.kindwise.kindwise_adapter import KindwiseAdapter
from src.adapters.ai.plantnet.plantnet_adapter import PlantNetAdapter
from src.adapters.cache.redis_health_raw_response_repository import (
    RedisHealthRawResponseRepository,
)
from src.adapters.cache.redis_otp_repository import RedisOtpRepository
from src.adapters.cache.redis_token_repository import RedisTokenRepository
from src.adapters.email.ses_email_sender import SesEmailSender
from src.adapters.events.celery_publisher import CeleryPublisher
from src.adapters.notifications.firebase_adapter import FirebaseAdapter
from src.adapters.resilience import (
    CircuitBreaker,
    CircuitBreakerHealthAnalyzer,
    CircuitBreakerPlantIdentifier,
)
from src.adapters.security.bcrypt_hasher import BcryptHasher
from src.adapters.storage.s3_image_storage import S3ImageStorage
from src.adapters.weather.nominatim_geocoder import NominatimGeocoder
from src.adapters.weather.open_meteo_adapter import OpenMeteoAdapter
from src.infrastructure.settings import Settings


class AdaptersContainer(containers.DeclarativeContainer):
    settings: providers.Dependency[Settings] = providers.Dependency()

    weather_http = providers.Singleton(httpx.AsyncClient)
    password_hasher = providers.Singleton(BcryptHasher)
    domain_publisher = providers.Singleton(CeleryPublisher)

    redis = providers.Singleton(
        Redis.from_url,
        url=settings.provided.redis_url,
        decode_responses=False,
        socket_timeout=settings.provided.redis_socket_timeout_seconds,
        socket_connect_timeout=settings.provided.redis_connect_timeout_seconds,
    )

    token_repository = providers.Singleton(
        RedisTokenRepository,
        redis=redis,
    )

    otp_repository = providers.Singleton(
        RedisOtpRepository,
        redis=redis,
    )

    health_raw_response_repository = providers.Singleton(
        RedisHealthRawResponseRepository,
        redis=redis,
    )

    email_sender = providers.Singleton(
        SesEmailSender,
        region=settings.provided.aws_region,
        sender_email=settings.provided.ses_sender_email,
    )

    image_storage = providers.Singleton(
        S3ImageStorage,
        bucket_name=settings.provided.s3_bucket,
        region=settings.provided.aws_region,
        aws_access_key_id=settings.provided.aws_access_key_id,
        aws_secret_access_key=settings.provided.aws_secret_access_key,
    )

    notification_sender = providers.Singleton(
        FirebaseAdapter,
        credentials_path=settings.provided.google_application_credentials,
    )

    # Kindwise atende identificação e saúde: um único breaker por provedor
    kindwise_breaker = providers.Singleton(CircuitBreaker, name="Kindwise")
    plantnet_breaker = providers.Singleton(CircuitBreaker, name="PlantNet")

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

    plant_enricher = providers.Singleton(
        GeminiAdapter,
        api_key=settings.provided.gemini_api_key,
    )

    geocoder = providers.Singleton(
        NominatimGeocoder,
        client=weather_http,
    )

    weather_service = providers.Singleton(
        OpenMeteoAdapter,
        client=weather_http,
        geocoder=geocoder,
    )