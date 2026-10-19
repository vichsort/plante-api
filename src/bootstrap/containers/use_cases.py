from dependency_injector import containers, providers

from src.domain.ports.health_analyzer import IHealthAnalyzer
from src.domain.ports.health_enricher import IHealthEnricher
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.use_cases.diagnose_health_use_case import DiagnoseHealthUseCase
from src.domain.use_cases.get_health_history_use_case import GetHealthHistoryUseCase
from src.domain.use_cases.give_health_feedback_use_case import GiveHealthFeedbackUseCase
from src.domain.use_cases.list_user_achievements_use_case import (
    ListUserAchievementsUseCase,
)
from src.modules.garden import IPlantLookup
from src.modules.identity import IUserDirectory
from src.modules.subscription import ITokenWallet
from src.modules.training import ITrainingRecorder
from src.shared.domain import IImageSanitizer, IImageStorage


class UseCasesContainer(containers.DeclarativeContainer):
    """Use cases do código antigo (saúde e conquistas): perde um grupo a cada módulo migrado."""

    unit_of_work: providers.Dependency[IUnitOfWork] = providers.Dependency()

    health_analyzer: providers.Dependency[IHealthAnalyzer] = providers.Dependency()
    health_enricher: providers.Dependency[IHealthEnricher] = providers.Dependency()
    image_storage: providers.Dependency[IImageStorage] = providers.Dependency()
    image_sanitizer: providers.Dependency[IImageSanitizer] = providers.Dependency()
    training_recorder: providers.Dependency[ITrainingRecorder] = providers.Dependency()
    token_wallet: providers.Dependency[ITokenWallet] = providers.Dependency()
    user_directory: providers.Dependency[IUserDirectory] = providers.Dependency()
    plant_lookup: providers.Dependency[IPlantLookup] = providers.Dependency()

    give_health_feedback_use_case = providers.Factory(
        GiveHealthFeedbackUseCase,
        uow=unit_of_work,
        training=training_recorder,
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
        plants=plant_lookup,
    )

    get_health_history_use_case = providers.Factory(
        GetHealthHistoryUseCase,
        uow=unit_of_work,
        plants=plant_lookup,
    )
