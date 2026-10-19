from dataclasses import dataclass

from src.modules.achievements.domain.ports.achievement_repository import (
    AchievementView,
)
from src.modules.achievements.domain.ports.unit_of_work import IAchievementsUnitOfWork
from src.shared.domain import UserId


@dataclass(frozen=True)
class ListUserAchievementsInputDTO:
    user_id: UserId

class ListUserAchievementsUseCase:
    raises = ()

    def __init__(self, uow: IAchievementsUnitOfWork) -> None:
        self.uow = uow

    async def execute(self, dto: ListUserAchievementsInputDTO) -> list[AchievementView]:
        async with self.uow as uow:
            return await uow.achievements.get_user_achievements_view(dto.user_id)
