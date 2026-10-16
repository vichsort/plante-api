from dataclasses import dataclass

from src.domain.ports.achievement_repository import (
    AchievementView,
)
from src.domain.ports.unit_of_work import IUnitOfWork
from src.shared.domain import UserId


@dataclass(frozen=True)
class ListUserAchievementsInputDTO:
    user_id: UserId

class ListUserAchievementsUseCase:
    raises = ()

    def __init__(self, uow: IUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, dto: ListUserAchievementsInputDTO) -> list[AchievementView]:
        async with self.uow as uow:
            return await uow.achievements.get_user_achievements_view(dto.user_id)
