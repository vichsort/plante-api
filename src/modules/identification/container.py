from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.catalog import ISpeciesRegistry
from src.modules.identification.adapters.consensus.identifier import ConsensusIdentifier
from src.modules.identification.adapters.kindwise.identifier import KindwiseIdentifier
from src.modules.identification.adapters.persistence.unit_of_work import (
    SqlAlchemyIdentificationUnitOfWork,
)
from src.modules.identification.adapters.plantnet.identifier import PlantNetIdentifier
from src.modules.identification.adapters.resilience.circuit_breaker import (
    CircuitBreakerPlantIdentifier,
)
from src.modules.identification.domain.ports.plant_identifier import IPlantIdentifier
from src.modules.identification.domain.services.identification_lookup import (
    IdentificationLookup,
)
from src.modules.identification.domain.use_cases.give_feedback import (
    GiveIdentificationFeedbackUseCase,
)
from src.modules.identification.domain.use_cases.identify_plant import (
    IdentifyPlantUseCase,
)
from src.modules.identity import IUserDirectory
from src.modules.subscription import ITokenWallet
from src.modules.training import ITrainingRecorder
from src.shared.adapters import CircuitBreaker, KindwiseClient
from src.shared.domain import IDomainPublisher, IImageSanitizer, IImageStorage


def _pick_identifier(consensus_enabled: bool, consensus: IPlantIdentifier, kindwise: IPlantIdentifier) -> IPlantIdentifier:
    """`CONSENSUS_ENABLED`: Kindwise e PlantNet juntos, ou só o Kindwise."""
    return consensus if consensus_enabled else kindwise


class IdentificationContainer(containers.DeclarativeContainer):
    session_factory: providers.Dependency[async_sessionmaker[AsyncSession]] = providers.Dependency()
    publisher: providers.Dependency[IDomainPublisher] = providers.Dependency()
    sanitizer: providers.Dependency[IImageSanitizer] = providers.Dependency()
    storage: providers.Dependency[IImageStorage] = providers.Dependency()
    # Um breaker por provedor, da composição: o do Kindwise também protege a saúde
    kindwise_client: providers.Dependency[KindwiseClient] = providers.Dependency()
    kindwise_breaker: providers.Dependency[CircuitBreaker] = providers.Dependency()
    plantnet_breaker: providers.Dependency[CircuitBreaker] = providers.Dependency()
    plantnet_api_key: providers.Dependency[str | None] = providers.Dependency()
    consensus_enabled: providers.Dependency[bool] = providers.Dependency()
    users: providers.Dependency[IUserDirectory] = providers.Dependency()
    wallet: providers.Dependency[ITokenWallet] = providers.Dependency()
    training: providers.Dependency[ITrainingRecorder] = providers.Dependency()
    catalog: providers.Dependency[ISpeciesRegistry] = providers.Dependency()

    unit_of_work = providers.Factory(SqlAlchemyIdentificationUnitOfWork, session_factory=session_factory)
    lookup = providers.Factory(IdentificationLookup, uow=unit_of_work)

    kindwise = providers.Singleton(KindwiseIdentifier, client=kindwise_client)
    plantnet = providers.Singleton(PlantNetIdentifier, api_key=plantnet_api_key)
    kindwise_identifier = providers.Singleton(CircuitBreakerPlantIdentifier, inner=kindwise, breaker=kindwise_breaker)
    plantnet_identifier = providers.Singleton(CircuitBreakerPlantIdentifier, inner=plantnet, breaker=plantnet_breaker)
    consensus_identifier = providers.Singleton(
        ConsensusIdentifier,
        kindwise=kindwise_identifier,
        plantnet=plantnet_identifier,
    )
    plant_identifier = providers.Callable(
        _pick_identifier,
        consensus_enabled=consensus_enabled,
        consensus=consensus_identifier,
        kindwise=kindwise_identifier,
    )

    identify_plant_use_case = providers.Factory(
        IdentifyPlantUseCase,
        uow=unit_of_work,
        sanitizer=sanitizer,
        plant_identifier=plant_identifier,
        storage=storage,
        publisher=publisher,
        users=users,
        wallet=wallet,
        training=training,
        catalog=catalog,
    )
    give_feedback_use_case = providers.Factory(
        GiveIdentificationFeedbackUseCase,
        uow=unit_of_work,
        training=training,
    )
