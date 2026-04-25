from dataclasses import dataclass
from src.domain.ports.achievement_repository import IAchievementRepository

@dataclass(frozen=True)
class ListUserAchievementsInputDTO:
    user_id: int

class ListUserAchievementsUseCase:
    def __init__(self, achievement_repo: IAchievementRepository) -> None:
        self.achievement_repo = achievement_repo

    async def execute(self, dto: ListUserAchievementsInputDTO) -> list[dict]:
        return await self.achievement_repo.get_user_achievements_view(dto.user_id)