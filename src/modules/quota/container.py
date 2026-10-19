from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.quota.adapters.persistence.unit_of_work import (
    SqlAlchemyQuotaUnitOfWork,
)
from src.modules.quota.domain.policies.quota_policy import QuotaPolicy
from src.modules.quota.domain.services.garden_quota import GardenQuota
from src.modules.quota.domain.services.token_wallet import TokenWallet
from src.modules.quota.domain.value_objects.level import LevelLimits
from src.shared.domain import LocalCalendar


class QuotaContainer(containers.DeclarativeContainer):
    session_factory: providers.Dependency[async_sessionmaker[AsyncSession]] = providers.Dependency()
    calendar: providers.Dependency[LocalCalendar] = providers.Dependency()
    limits: providers.Dependency[LevelLimits] = providers.Dependency()

    unit_of_work = providers.Factory(SqlAlchemyQuotaUnitOfWork, session_factory=session_factory)
    policy = providers.Singleton(QuotaPolicy, limits=limits)
    token_wallet = providers.Factory(TokenWallet, uow=unit_of_work, calendar=calendar, policy=policy)
    garden_quota = providers.Factory(GardenQuota, uow=unit_of_work, policy=policy)
