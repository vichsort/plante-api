from dependency_injector import containers, providers
import httpx
from redis.asyncio import Redis

from src.adapters.security.bcrypt_hasher import BcryptHasher
from src.adapters.events.celery_publisher import CeleryPublisher
from src.adapters.cache.redis_health_raw_response_repository import RedisHealthRawResponseRepository
from src.adapters.cache.redis_otp_repository import RedisOtpRepository
from src.adapters.cache.redis_token_repository import RedisTokenRepository
from src.adapters.email.ses_email_sender import SesEmailSender
from src.adapters.storage.s3_image_storage import S3ImageStorage
from src.adapters.notifications.firebase_adapter import FirebaseAdapter
from src.adapters.ai.kindwise.kindwise_adapter import KindwiseAdapter
from src.adapters.ai.gemini.gemini_adapter import GeminiAdapter
from src.adapters.weather.nominatim_geocoder import NominatimGeocoder
from src.adapters.weather.open_meteo_adapter import OpenMeteoAdapter
from src.adapters.ai.plantnet.plantnet_adapter import PlantNetAdapter
from src.adapters.ai.consensus.consensus_adapter import ConsensusIdentifier

class AdaptersContainer(containers.DeclarativeContainer):
    settings = providers.Dependency()

    weather_http = providers.Singleton(httpx.AsyncClient)
    password_hasher = providers.Singleton(BcryptHasher)
    domain_publisher = providers.Singleton(CeleryPublisher)

    redis = providers.Singleton(
        Redis.from_url,
        url=settings.provided.redis_url,
        decode_responses=False,
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
        bucket=settings.provided.s3_bucket,
        region=settings.provided.aws_region,
        aws_access_key_id=settings.provided.aws_access_key_id,
        aws_secret_access_key=settings.provided.aws_secret_access_key,
    )

    notification_sender = providers.Singleton(
        FirebaseAdapter,
        credentials_path=settings.provided.google_application_credentials,
    )

    kindwise_identifier = providers.Singleton(
        KindwiseAdapter,
        api_key=settings.provided.plant_id_api_key,
    )

    plantnet_identifier = providers.Singleton(
        PlantNetAdapter,
        api_key=settings.provided.plantnet_api_key,
    )

    consensus_identifier = providers.Singleton(
        ConsensusIdentifier,
        kindwise=kindwise_identifier,
        plantnet=plantnet_identifier,
    )

    plant_identifier = providers.Selector(
        settings.provided.consensus_enabled,
        true=consensus_identifier,
        false=kindwise_identifier,
    )

    health_analyzer = providers.Singleton(
        KindwiseAdapter,
        api_key=settings.provided.plant_id_api_key,
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