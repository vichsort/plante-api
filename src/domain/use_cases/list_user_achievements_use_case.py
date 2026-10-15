from dataclasses import dataclass

from src.domain.ports.achievement_repository import (
    AchievementView,
    IAchievementRepository,
)
from src.domain.value_objects.ids import UserId


@dataclass(frozen=True)
class ListUserAchievementsInputDTO:
    user_id: UserId

class ListUserAchievementsUseCase:
    raises = ()

    def __init__(self, achievement_repo: IAchievementRepository) -> None:
        self.achievement_repo = achievement_repo

    async def execute(self, dto: ListUserAchievementsInputDTO) -> list[AchievementView]:
        return await self.achievement_repo.get_user_achievements_view(dto.user_id)