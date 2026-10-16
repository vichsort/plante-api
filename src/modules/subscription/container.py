from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.subscription.adapters.persistence.unit_of_work import (
    SqlAlchemySubscriptionUnitOfWork,
)
from src.modules.subscription.domain.services.garden_quota import GardenQuota
from src.modules.subscription.domain.services.token_wallet import TokenWallet
from src.modules.subscription.domain.use_cases.upgrade_subscription import (
    UpgradeSubscriptionUseCase,
)
from src.shared.domain import IDomainPublisher, LocalCalendar


class SubscriptionContainer(containers.DeclarativeContainer):
    session_factory: providers.Dependency[async_sessionmaker[AsyncSession]] = providers.Dependency()
    calendar: providers.Dependency[LocalCalendar] = providers.Dependency()
    publisher: providers.Dependency[IDomainPublisher] = providers.Dependency()

    unit_of_work = providers.Factory(SqlAlchemySubscriptionUnitOfWork, session_factory=session_factory)
    token_wallet = providers.Factory(TokenWallet, uow=unit_of_work, calendar=calendar)
    garden_quota = providers.Factory(GardenQuota, uow=unit_of_work)

    upgrade_subscription_use_case = providers.Factory(
        UpgradeSubscriptionUseCase,
        uow=unit_of_work,
        publisher=publisher,
    )
