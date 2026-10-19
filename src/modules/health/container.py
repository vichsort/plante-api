from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.garden import IPlantLookup
from src.modules.health.adapters.gemini.enricher import GeminiHealthEnricher
from src.modules.health.adapters.kindwise.analyzer import KindwiseHealthAnalyzer
from src.modules.health.adapters.persistence.unit_of_work import (
    SqlAlchemyHealthUnitOfWork,
)
from src.modules.health.adapters.resilience.circuit_breaker import (
    CircuitBreakerHealthAnalyzer,
)
from src.modules.health.domain.use_cases.diagnose import DiagnoseHealthUseCase
from src.modules.health.domain.use_cases.get_history import GetHealthHistoryUseCase
from src.modules.health.domain.use_cases.give_feedback import (
    GiveHealthFeedbackUseCase,
)
from src.modules.identity import IUserDirectory
from src.modules.subscription import ITokenWallet
from src.modules.training import ITrainingRecorder
from src.shared.adapters import CircuitBreaker, KindwiseClient
from src.shared.domain import IImageSanitizer, IImageStorage


class HealthContainer(containers.DeclarativeContainer):
    session_factory: providers.Dependency[async_sessionmaker[AsyncSession]] = providers.Dependency()
    sanitizer: providers.Dependency[IImageSanitizer] = providers.Dependency()
    storage: providers.Dependency[IImageStorage] = providers.Dependency()
    # Cliente e breaker do Kindwise vêm da composição: os mesmos da identificação
    kindwise_client: providers.Dependency[KindwiseClient] = providers.Dependency()
    kindwise_breaker: providers.Dependency[CircuitBreaker] = providers.Dependency()
    gemini_api_key: providers.Dependency[str | None] = providers.Dependency()
    users: providers.Dependency[IUserDirectory] = providers.Dependency()
    wallet: providers.Dependency[ITokenWallet] = providers.Dependency()
    training: providers.Dependency[ITrainingRecorder] = providers.Dependency()
    plants: providers.Dependency[IPlantLookup] = providers.Dependency()

    unit_of_work = providers.Factory(SqlAlchemyHealthUnitOfWork, session_factory=session_factory)

    kindwise = providers.Singleton(KindwiseHealthAnalyzer, client=kindwise_client)
    analyzer = providers.Singleton(CircuitBreakerHealthAnalyzer, inner=kindwise, breaker=kindwise_breaker)
    enricher = providers.Singleton(GeminiHealthEnricher, api_key=gemini_api_key)

    diagnose_use_case = providers.Factory(
        DiagnoseHealthUseCase,
        uow=unit_of_work,
        sanitizer=sanitizer,
        health_analyzer=analyzer,
        enricher=enricher,
        storage=storage,
        users=users,
        wallet=wallet,
        training=training,
        plants=plants,
    )
    give_feedback_use_case = providers.Factory(GiveHealthFeedbackUseCase, uow=unit_of_work, training=training)
    get_history_use_case = providers.Factory(GetHealthHistoryUseCase, uow=unit_of_work, plants=plants)
