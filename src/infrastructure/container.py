from dependency_injector import containers, providers

from src.infrastructure.settings import Settings
from src.infrastructure.containers.infra import InfraContainer
from src.infrastructure.containers.adapters import AdaptersContainer
from src.infrastructure.containers.repositories import RepositoriesContainer
from src.infrastructure.containers.use_cases import UseCasesContainer

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

    repositories = providers.Container(
        RepositoriesContainer,
        session=infra.session,
    )

    use_cases = providers.Container(
        UseCasesContainer,
        settings=settings,
        user_repository=repositories.user_repository,
        token_repository=adapters.token_repository,
        otp_repository=adapters.otp_repository,
        user_plant_repository=repositories.user_plant_repository,
        plant_species_repository=repositories.plant_species_repository,
        identification_sample_repository=repositories.identification_sample_repository,
        health_record_repository=repositories.health_record_repository,
        health_identification_sample_repository=repositories.health_identification_sample_repository,
        health_raw_response_repository=adapters.health_raw_response_repository,
        plant_nutritional_repository=repositories.plant_nutritional_repository,
        achievement_repository=repositories.achievement_repository,
        password_hasher=adapters.password_hasher,
        email_sender=adapters.email_sender,
        domain_publisher=adapters.domain_publisher,
        plant_identifier=adapters.plant_identifier,
        health_analyzer=adapters.health_analyzer,
        plant_enricher=adapters.plant_enricher,
        image_storage=adapters.image_storage,
    )