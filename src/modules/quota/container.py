from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.quota.adapters.persistence.unit_of_work import (
    SqlAlchemyQuotaUnitOfWork,
)
from src.modules.quota.adapters.redis.usage_counter import RedisUsageCounter
from src.modules.quota.domain.policies.quota_policy import QuotaPolicy
from src.modules.quota.domain.services.garden_quota import GardenQuota
from src.modules.quota.domain.services.provider_budget import ProviderBudget
from src.modules.quota.domain.services.token_wallet import TokenWallet
from src.modules.quota.domain.use_cases.grant_extended_quota import (
    GrantExtendedQuotaUseCase,
)
from src.modules.quota.domain.use_cases.revoke_extended_quota import (
    RevokeExtendedQuotaUseCase,
)
from src.modules.quota.domain.value_objects.level import LevelLimits
from src.shared.adapters import RedisClient
from src.shared.domain import LocalCalendar


class QuotaContainer(containers.DeclarativeContainer):
    session_factory: providers.Dependency[async_sessionmaker[AsyncSession]] = providers.Dependency()
    calendar: providers.Dependency[LocalCalendar] = providers.Dependency()
    limits: providers.Dependency[LevelLimits] = providers.Dependency()
    redis: providers.Dependency[RedisClient] = providers.Dependency()
    provider_daily_limit: providers.Dependency[int] = providers.Dependency()

    unit_of_work = providers.Factory(SqlAlchemyQuotaUnitOfWork, session_factory=session_factory)
    policy = providers.Singleton(QuotaPolicy, limits=limits)
    token_wallet = providers.Factory(TokenWallet, uow=unit_of_work, calendar=calendar, policy=policy)
    garden_quota = providers.Factory(GardenQuota, uow=unit_of_work, policy=policy)
    provider_calls = providers.Singleton(RedisUsageCounter, redis=redis, name="provider_calls")
    provider_budget = providers.Factory(
        ProviderBudget, counter=provider_calls, calendar=calendar, daily_limit=provider_daily_limit,
    )

    # The maintainer's command (`src.bootstrap.quota_admin`); no HTTP route
    grant_extended_quota = providers.Factory(GrantExtendedQuotaUseCase, uow=unit_of_work)
    revoke_extended_quota = providers.Factory(RevokeExtendedQuotaUseCase, uow=unit_of_work)
