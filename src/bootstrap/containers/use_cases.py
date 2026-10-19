from dependency_injector import containers, providers

from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.use_cases.list_user_achievements_use_case import (
    ListUserAchievementsUseCase,
)


class UseCasesContainer(containers.DeclarativeContainer):
    """Use cases do código antigo (só conquistas): sai quando o módulo delas migrar."""

    unit_of_work: providers.Dependency[IUnitOfWork] = providers.Dependency()

    list_user_achievements_use_case = providers.Factory(
        ListUserAchievementsUseCase,
        uow=unit_of_work,
    )
