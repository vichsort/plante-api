from dependency_injector import containers, providers

from src.bootstrap.containers.adapters import AdaptersContainer
from src.bootstrap.containers.infra import InfraContainer
from src.bootstrap.containers.use_cases import UseCasesContainer
from src.bootstrap.settings import Settings
from src.modules.catalog.container import CatalogContainer
from src.modules.training.container import TrainingContainer


class Container(containers.DeclarativeContainer):

    settings = providers.Singleton(Settings)

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

    use_cases = providers.Container(
        UseCasesContainer,
        settings=settings,
        unit_of_work=infra.unit_of_work,
        token_repository=adapters.token_repository,
        otp_repository=adapters.otp_repository,
        password_hasher=adapters.password_hasher,
        email_sender=adapters.email_sender,
        domain_publisher=adapters.domain_publisher,
        plant_identifier=adapters.plant_identifier,
        health_analyzer=adapters.health_analyzer,
        health_enricher=adapters.health_enricher,
        species_enricher=catalog.species_enricher,
        species_registry=catalog.registry,
        image_storage=adapters.image_storage,
        image_sanitizer=adapters.image_sanitizer,
        token_service=adapters.token_service,
        training_recorder=training.recorder,
    )