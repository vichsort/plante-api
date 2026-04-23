from dataclasses import dataclass
from src.domain.ports.achievement_repository import IAchievementRepository

@dataclass(frozen=True)
class ListUserAchievementsInputDTO:
    user_id: int

class ListUserAchievementsUseCase:
    def __init__(self, achievement_repo: IAchievementRepository):
        self.achievement_repo = achievement_repo

    def execute(self, dto: ListUserAchievementsInputDTO) -> list[dict]:
        # Devolve a lista formatada: [{"badge": "FIRST_BLOOM", "unlocked_at": "2024-05-10T10:00:00Z"}]
        return self.achievement_repo.get_user_achievements_view(dto.user_id)