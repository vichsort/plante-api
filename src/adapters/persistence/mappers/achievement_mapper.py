from src.adapters.persistence.models.achievement_model import AchievementModel
from src.domain.ports.achievement_repository import AchievementView
from src.domain.value_objects.ids import AchievementId


class AchievementMapper:
    @staticmethod
    def to_view(model: AchievementModel) -> AchievementView:
        return AchievementView(
            id=AchievementId(model.id),
            badge_code=model.badge_code,
            unlocked_at=model.unlocked_at,
        )
