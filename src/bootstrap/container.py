from dependency_injector import containers, providers

from src.bootstrap.containers.adapters import AdaptersContainer
from src.bootstrap.containers.infra import InfraContainer
from src.bootstrap.settings import Settings
from src.modules.achievements.container import AchievementsContainer
from src.modules.catalog.container import CatalogContainer
from src.modules.garden.container import GardenContainer
from src.modules.health.container import HealthContainer
from src.modules.identification.container import IdentificationContainer
from src.modules.identity.container import IdentityContainer
from src.modules.quota import LevelLimits, QuotaLimits
from src.modules.quota.container import QuotaContainer
from src.modules.training.container import TrainingContainer
from src.shared.domain import LocalCalendar


class Container(containers.DeclarativeContainer):

    settings = providers.Singleton(Settings)

    # Que dia é para o usuário (rega e cota diária)
    calendar = providers.Singleton(LocalCalendar.from_name, settings.provided.local_timezone)

    infra = providers.Container(
        InfraContainer,
        settings=settings,
    )

    adapters = providers.Container(
        AdaptersContainer,
        settings=settings,
    )

    catalog = providers.Container(
        CatalogContainer,
        session_factory=infra.session_factory,
        gemini_api_key=settings.provided.gemini_api_key,
    )

    training = providers.Container(
        TrainingContainer,
        session_factory=infra.session_factory,
    )

    identity = providers.Container(
        IdentityContainer,
        session_factory=infra.session_factory,
        redis=adapters.redis,
        publisher=adapters.domain_publisher,
        storage=adapters.image_storage,
        secret_key=settings.provided.secret_key,
        jwt_algorithm=settings.provided.jwt_algorithm,
        aws_region=settings.provided.aws_region,
        email_backend=settings.provided.email_backend,
        email_from=settings.provided.email_from,
        email_verification_required=settings.provided.email_verification_required,
        smtp_host=settings.provided.smtp_host,
        smtp_port=settings.provided.smtp_port,
        smtp_username=settings.provided.smtp_username,
        smtp_password=settings.provided.smtp_password,
        smtp_security=settings.provided.smtp_security,
        turnstile_secret_key=settings.provided.turnstile_secret_key,
        terms_version=settings.provided.terms_version,
        terms_url=settings.provided.terms_url,
    )

    quota_limits = providers.Singleton(
        LevelLimits,
        standard=providers.Factory(
            QuotaLimits,
            max_plants=settings.provided.quota_standard_max_plants,
            daily_tokens=settings.provided.quota_standard_daily_tokens,
        ),
        extended=providers.Factory(
            QuotaLimits,
            max_plants=settings.provided.quota_extended_max_plants,
            daily_tokens=settings.provided.quota_extended_daily_tokens,
        ),
    )

    quota = providers.Container(
        QuotaContainer,
        session_factory=infra.session_factory,
        calendar=calendar,
        limits=quota_limits,
        redis=adapters.redis,
        provider_daily_limit=settings.provided.provider_daily_limit,
    )

    identification = providers.Container(
        IdentificationContainer,
        session_factory=infra.session_factory,
        publisher=adapters.domain_publisher,
        sanitizer=adapters.image_sanitizer,
        storage=adapters.image_storage,
        kindwise_client=adapters.kindwise_client,
        kindwise_breaker=adapters.kindwise_breaker,
        plantnet_breaker=adapters.plantnet_breaker,
        plantnet_api_key=settings.provided.plantnet_api_key,
        consensus_enabled=settings.provided.consensus_enabled,
        users=identity.directory,
        wallet=quota.token_wallet,
        budget=quota.provider_budget,
        training=training.recorder,
        catalog=catalog.registry,
    )

    garden = providers.Container(
        GardenContainer,
        session_factory=infra.session_factory,
        publisher=adapters.domain_publisher,
        calendar=calendar,
        users=identity.directory,
        quota=quota.garden_quota,
        training=training.recorder,
        identifications=identification.lookup,
        catalog=catalog.registry,
        storage=adapters.image_storage,
    )

    health = providers.Container(
        HealthContainer,
        session_factory=infra.session_factory,
        sanitizer=adapters.image_sanitizer,
        storage=adapters.image_storage,
        kindwise_client=adapters.kindwise_client,
        kindwise_breaker=adapters.kindwise_breaker,
        gemini_api_key=settings.provided.gemini_api_key,
        users=identity.directory,
        wallet=quota.token_wallet,
        budget=quota.provider_budget,
        training=training.recorder,
        plants=garden.lookup,
    )

    achievements = providers.Container(
        AchievementsContainer,
        session_factory=infra.session_factory,
    )
