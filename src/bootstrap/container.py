from dependency_injector import containers, providers

from src.bootstrap.containers.adapters import AdaptersContainer
from src.bootstrap.containers.infra import InfraContainer
from src.bootstrap.containers.use_cases import UseCasesContainer
from src.bootstrap.settings import Settings
from src.modules.catalog.container import CatalogContainer
from src.modules.identification.container import IdentificationContainer
from src.modules.identity.container import IdentityContainer
from src.modules.subscription.container import SubscriptionContainer
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
        secret_key=settings.provided.secret_key,
        jwt_algorithm=settings.provided.jwt_algorithm,
        aws_region=settings.provided.aws_region,
        ses_sender_email=settings.provided.ses_sender_email,
    )

    subscription = providers.Container(
        SubscriptionContainer,
        session_factory=infra.session_factory,
        calendar=calendar,
        publisher=adapters.domain_publisher,
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
        wallet=subscription.token_wallet,
        training=training.recorder,
        catalog=catalog.registry,
    )

    use_cases = providers.Container(
        UseCasesContainer,
        settings=settings,
        unit_of_work=infra.unit_of_work,
        domain_publisher=adapters.domain_publisher,
        health_analyzer=adapters.health_analyzer,
        health_enricher=adapters.health_enricher,
        species_registry=catalog.registry,
        image_storage=adapters.image_storage,
        image_sanitizer=adapters.image_sanitizer,
        training_recorder=training.recorder,
        token_wallet=subscription.token_wallet,
        garden_quota=subscription.garden_quota,
        local_calendar=calendar,
        user_directory=identity.directory,
        identification_lookup=identification.lookup,
    )