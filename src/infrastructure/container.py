from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
import httpx

from src.infrastructure.settings import Settings
from src.adapters.persistence.session import build_session_factory

# Repositórios
from src.adapters.persistence.repositories.user_repository import UserRepository
from src.adapters.persistence.repositories.user_plant_repository import UserPlantRepository
from src.adapters.persistence.repositories.plant_species_repository import PlantSpeciesRepository
from src.adapters.persistence.repositories.plant_nutritional_repository import PlantNutritionalRepository
from src.adapters.persistence.repositories.plant_reference_image_repository import PlantReferenceImageRepository
from src.adapters.persistence.repositories.health_record_repository import HealthRecordRepository
from src.adapters.persistence.repositories.identification_sample_repository import IdentificationSampleRepository
from src.adapters.persistence.repositories.achievement_repository import AchievementRepository

# Use cases
from src.domain.use_cases.change_email_use_case import ChangeEmailUseCase
from src.domain.use_cases.change_password_use_case import ChangePasswordUseCase
from src.domain.use_cases.register_user_use_case import RegisterUserUseCase
from src.domain.use_cases.verify_email_use_case import VerifyEmailUseCase
from src.domain.use_cases.upgrade_subscription_use_case import UpgradeSubscriptionUseCase
from src.domain.use_cases.update_location_fallback_use_case import UpdateLocationFallbackUseCase
from src.domain.use_cases.add_plant_to_garden_use_case import AddPlantToGardenUseCase
from src.domain.use_cases.delete_user_plant_use_case import DeleteUserPlantUseCase
from src.domain.use_cases.get_user_garden_use_case import GetUserGardenUseCase
from src.domain.use_cases.get_plant_details_use_case import GetPlantDetailsUseCase
from src.domain.use_cases.identify_plant_use_case import IdentifyPlantUseCase
from src.domain.use_cases.enrich_plant_species_use_case import EnrichPlantSpeciesUseCase
from src.domain.use_cases.water_plant_use_case import WaterPlantUseCase
from src.domain.use_cases.break_streak_cron_use_case import BreakStreakCronUseCase
from src.domain.use_cases.list_user_achievements_use_case import ListUserAchievementsUseCase
from src.domain.use_cases.login_use_case import LoginUseCase
from src.domain.use_cases.refresh_token_use_case import RefreshTokenUseCase
from src.domain.use_cases.logout_use_case import LogoutUseCase
from src.domain.use_cases.diagnose_health_use_case import DiagnoseHealthUseCase
from src.domain.use_cases.get_health_history_use_case import GetHealthHistoryUseCase

# Adapters
from src.adapters.security.bcrypt_hasher import BcryptHasher
from src.adapters.cache.redis_otp_repository import RedisOtpRepository
from src.adapters.notifications.firebase_adapter import FirebaseAdapter
from src.adapters.ai.gemini.gemini_adapter import GeminiAdapter
from src.adapters.ai.kindwise.kindwise_adapter import KindwiseAdapter
from src.adapters.email.ses_email_sender import SesEmailSender
from src.adapters.weather.nominatim_geocoder import NominatimGeocoder
from src.adapters.weather.open_meteo_adapter import OpenMeteoAdapter
from src.adapters.cache.redis_token_repository import RedisTokenRepository
from src.adapters.events.celery_publisher import CeleryPublisher
from src.adapters.storage.s3_image_storage import S3ImageStorage

class Container(containers.DeclarativeContainer):

    # ------------------------------------------------------------------ #
    # Config                                                               #
    # ------------------------------------------------------------------ #
    settings = providers.Singleton(Settings)

    # ------------------------------------------------------------------ #
    # Infra                                                                #
    # ------------------------------------------------------------------ #
    session_factory = providers.Singleton(
        build_session_factory,
        settings=settings,
    )

    session = providers.Resource(
        AsyncSession,
        bind=session_factory,
    )

    # ------------------------------------------------------------------ #
    # Repositórios                                                         #
    # ------------------------------------------------------------------ #
    user_repository = providers.Factory(
        UserRepository,
        session=session,
    )

    user_plant_repository = providers.Factory(
        UserPlantRepository,
        session=session,
    )

    plant_species_repository = providers.Factory(
        PlantSpeciesRepository,
        session=session,
    )

    plant_nutritional_repository = providers.Factory(
        PlantNutritionalRepository,
        session=session,
    )

    plant_reference_image_repository = providers.Factory(
        PlantReferenceImageRepository,
        session=session,
    )

    health_record_repository = providers.Factory(
        HealthRecordRepository,
        session=session,
    )

    identification_sample_repository = providers.Factory(
        IdentificationSampleRepository,
        session=session,
    )

    achievement_repository = providers.Factory(
        AchievementRepository, 
        session=session
    )

    # ------------------------------------------------------------------ #
    # Adapters externos                                                  #
    # ------------------------------------------------------------------ #
    weather_http = providers.Singleton(httpx.AsyncClient)

    redis = providers.Singleton(
        Redis.from_url,
        url=settings.provided.redis_url,
        decode_responses=False,
    )

    email_sender = providers.Singleton(
        SesEmailSender,
        region=settings.provided.aws_region,
        sender_email=settings.provided.ses_sender_email,
    )

    password_hasher = providers.Singleton(BcryptHasher)

    domain_publisher = providers.Singleton(CeleryPublisher)

    image_storage = providers.Singleton(
        S3ImageStorage,
        bucket=settings.provided.s3_bucket,
        region=settings.provided.aws_region,
        aws_access_key_id=settings.provided.aws_access_key_id,
        aws_secret_access_key=settings.provided.aws_secret_access_key,
    )

    otp_repository = providers.Singleton(
        RedisOtpRepository,
        redis=redis,
    )

    notification_sender = providers.Singleton(
        FirebaseAdapter,
        credentials_path=settings.provided.google_application_credentials,
    )

    plant_identifier = providers.Singleton(
        KindwiseAdapter, 
        api_key=settings.provided.plant_id_api_key
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

    token_repository = providers.Singleton(
        RedisTokenRepository,
        redis=redis,
    )

    # ------------------------------------------------------------------ #
    # Use cases                                                            #
    # ------------------------------------------------------------------ #

    login_use_case = providers.Factory(
        LoginUseCase,
        user_repo=user_repository,
        hasher=password_hasher,
        token_repo=token_repository,
        secret_key=settings.provided.secret_key,
        algorithm=settings.provided.jwt_algorithm,
    )

    refresh_token_use_case = providers.Factory(
        RefreshTokenUseCase,
        token_repo=token_repository,
        secret_key=settings.provided.secret_key,
        algorithm=settings.provided.jwt_algorithm,
    )

    logout_use_case = providers.Factory(
        LogoutUseCase,
        token_repo=token_repository,
    )

    change_email_use_case = providers.Factory(
        ChangeEmailUseCase,
        user_repo=user_repository,
        otp_repo=otp_repository,
        hasher=password_hasher,
        email_sender=email_sender,
    )

    change_password_use_case = providers.Factory(
        ChangePasswordUseCase,
        user_repo=user_repository,
        hasher=password_hasher,
    )

    register_user_use_case = providers.Factory(
        RegisterUserUseCase,
        user_repo=user_repository,
        hasher=password_hasher,
        email_sender=email_sender,
        otp_repo=otp_repository,
        publisher=domain_publisher,
    )

    verify_email_use_case = providers.Factory(
        VerifyEmailUseCase,
        user_repo=user_repository,
        otp_repo=otp_repository,
    )

    upgrade_subscription_use_case = providers.Factory(
        UpgradeSubscriptionUseCase,
        user_repo=user_repository,
        publisher=domain_publisher
    )

    update_location_fallback_use_case = providers.Factory(
        UpdateLocationFallbackUseCase,
        user_repo=user_repository,
    )

    add_plant_to_garden_use_case = providers.Factory(
        AddPlantToGardenUseCase,
        user_repo=user_repository,
        user_plant_repo=user_plant_repository,
        species_repo=plant_species_repository,
        sample_repo=identification_sample_repository,
    )

    delete_user_plant_use_case = providers.Factory(
        DeleteUserPlantUseCase,
        user_repo=user_repository,
        user_plant_repo=user_plant_repository,
    )

    get_user_garden_use_case = providers.Factory(
        GetUserGardenUseCase,
        user_plant_repo=user_plant_repository,
    )

    get_plant_details_use_case = providers.Factory(
        GetPlantDetailsUseCase,
        user_plant_repo=user_plant_repository,
        species_repo=plant_species_repository,
        nutritional_repo=plant_nutritional_repository,
        health_repo=health_record_repository,
    )

    identify_plant_use_case = providers.Factory(
        IdentifyPlantUseCase,
        user_repo=user_repository,
        species_repo=plant_species_repository,
        sample_repo=identification_sample_repository,
        plant_identifier=plant_identifier,
    )

    enrich_plant_species_use_case = providers.Factory(
        EnrichPlantSpeciesUseCase,
        species_repo=plant_species_repository,
        nutritional_repo=plant_nutritional_repository,
        plant_enricher=plant_enricher,
    )

    water_plant_use_case = providers.Factory(
        WaterPlantUseCase,
        user_plant_repo=user_plant_repository,
    )

    break_streak_cron_use_case = providers.Factory(
        BreakStreakCronUseCase,
        user_plant_repo=user_plant_repository,
    )

    list_user_achievements_use_case = providers.Factory(
        ListUserAchievementsUseCase,
        achievement_repo=achievement_repository,
    )

    """
    NOTA PARA AMANHÃ: 
    - verificar prompts e coisas relativas as IAs.
    - cogitar refatorar ou diminuir esse arquivo aqui
    - fazer aquilo de pedir pra duas IA (kindwise e plantnet em conjunto)
    - fase R
    """

    diagnose_health_use_case = providers.Factory(
        DiagnoseHealthUseCase,
        user_repo=user_repository,
        user_plant_repo=user_plant_repository,
        health_repo=health_record_repository,
        health_analyzer=health_analyzer,
        plant_enricher=plant_enricher,
        storage=image_storage,
    )

    get_health_history_use_case = providers.Factory(
        GetHealthHistoryUseCase,
        user_plant_repo=user_plant_repository,
        health_repo=health_record_repository,
    )