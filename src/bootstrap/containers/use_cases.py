from dependency_injector import containers, providers

from src.bootstrap.settings import Settings
from src.domain.ports.health_analyzer import IHealthAnalyzer
from src.domain.ports.health_enricher import IHealthEnricher
from src.domain.ports.plant_identifier import IPlantIdentifier
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.use_cases.add_plant_to_garden_use_case import AddPlantToGardenUseCase
from src.domain.use_cases.break_streak_cron_use_case import BreakStreakCronUseCase
from src.domain.use_cases.delete_user_plant_use_case import DeleteUserPlantUseCase
from src.domain.use_cases.diagnose_health_use_case import DiagnoseHealthUseCase
from src.domain.use_cases.get_health_history_use_case import GetHealthHistoryUseCase
from src.domain.use_cases.get_plant_details_use_case import GetPlantDetailsUseCase
from src.domain.use_cases.get_user_garden_use_case import GetUserGardenUseCase
from src.domain.use_cases.give_health_feedback_use_case import GiveHealthFeedbackUseCase
from src.domain.use_cases.give_identification_feedback_use_case import (
    GiveIdentificationFeedbackUseCase,
)
from src.domain.use_cases.identify_plant_use_case import IdentifyPlantUseCase
from src.domain.use_cases.list_user_achievements_use_case import (
    ListUserAchievementsUseCase,
)
from src.domain.use_cases.water_plant_use_case import WaterPlantUseCase
from src.modules.catalog import ISpeciesRegistry
from src.modules.identity import IUserDirectory
from src.modules.subscription import IGardenQuota, ITokenWallet
from src.modules.training import ITrainingRecorder
from src.shared.domain import (
    IDomainPublisher,
    IImageSanitizer,
    IImageStorage,
    LocalCalendar,
)


class UseCasesContainer(containers.DeclarativeContainer):
    settings: providers.Dependency[Settings] = providers.Dependency()

    unit_of_work: providers.Dependency[IUnitOfWork] = providers.Dependency()

    domain_publisher: providers.Dependency[IDomainPublisher] = providers.Dependency()
    plant_identifier: providers.Dependency[IPlantIdentifier] = providers.Dependency()
    health_analyzer: providers.Dependency[IHealthAnalyzer] = providers.Dependency()
    health_enricher: providers.Dependency[IHealthEnricher] = providers.Dependency()
    species_registry: providers.Dependency[ISpeciesRegistry] = providers.Dependency()

    image_storage: providers.Dependency[IImageStorage] = providers.Dependency()
    image_sanitizer: providers.Dependency[IImageSanitizer] = providers.Dependency()
    training_recorder: providers.Dependency[ITrainingRecorder] = providers.Dependency()
    token_wallet: providers.Dependency[ITokenWallet] = providers.Dependency()
    garden_quota: providers.Dependency[IGardenQuota] = providers.Dependency()
    local_calendar: providers.Dependency[LocalCalendar] = providers.Dependency()
    user_directory: providers.Dependency[IUserDirectory] = providers.Dependency()

    add_plant_to_garden_use_case = providers.Factory(
        AddPlantToGardenUseCase,
        uow=unit_of_work,
        publisher=domain_publisher,
        calendar=local_calendar,
        users=user_directory,
        quota=garden_quota,
        training=training_recorder,
    )

    give_identification_feedback_use_case = providers.Factory(
        GiveIdentificationFeedbackUseCase,
        uow=unit_of_work,
        training=training_recorder,
    )

    give_health_feedback_use_case = providers.Factory(
        GiveHealthFeedbackUseCase,
        uow=unit_of_work,
        training=training_recorder,
    )

    delete_user_plant_use_case = providers.Factory(
        DeleteUserPlantUseCase,
        uow=unit_of_work,
    )

    get_user_garden_use_case = providers.Factory(
        GetUserGardenUseCase,
        uow=unit_of_work,
        calendar=local_calendar,
    )

    get_plant_details_use_case = providers.Factory(
        GetPlantDetailsUseCase,
        uow=unit_of_work,
        calendar=local_calendar,
        catalog=species_registry,
    )

    identify_plant_use_case = providers.Factory(
        IdentifyPlantUseCase,
        uow=unit_of_work,
        sanitizer=image_sanitizer,
        plant_identifier=plant_identifier,
        storage=image_storage,
        publisher=domain_publisher,
        users=user_directory,
        wallet=token_wallet,
        training=training_recorder,
        catalog=species_registry,
    )

    water_plant_use_case = providers.Factory(
        WaterPlantUseCase,
        uow=unit_of_work,
        publisher=domain_publisher,
        calendar=local_calendar,
    )

    break_streak_cron_use_case = providers.Factory(
        BreakStreakCronUseCase,
        uow=unit_of_work,
        publisher=domain_publisher,
        calendar=local_calendar,
    )

    list_user_achievements_use_case = providers.Factory(
        ListUserAchievementsUseCase,
        uow=unit_of_work,
    )

    diagnose_health_use_case = providers.Factory(
        DiagnoseHealthUseCase,
        uow=unit_of_work,
        sanitizer=image_sanitizer,
        health_analyzer=health_analyzer,
        plant_enricher=health_enricher,
        storage=image_storage,
        users=user_directory,
        wallet=token_wallet,
        training=training_recorder,
    )

    get_health_history_use_case = providers.Factory(
        GetHealthHistoryUseCase,
        uow=unit_of_work,
    )