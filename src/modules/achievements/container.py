from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.achievements.adapters.persistence.unit_of_work import (
    SqlAlchemyAchievementsUnitOfWork,
)
from src.modules.achievements.domain.use_cases.list_achievements import (
    ListUserAchievementsUseCase,
)


class AchievementsContainer(containers.DeclarativeContainer):
    session_factory: providers.Dependency[async_sessionmaker[AsyncSession]] = providers.Dependency()

    unit_of_work = providers.Factory(SqlAlchemyAchievementsUnitOfWork, session_factory=session_factory)
    list_achievements_use_case = providers.Factory(ListUserAchievementsUseCase, uow=unit_of_work)
