from src.adapters.persistence.models.achievement_model import AchievementModel

class AchievementMapper:
    @staticmethod
    def to_dict(model: AchievementModel) -> dict:
        return {
            "badge_code": model.badge_code,
            "unlocked_at": model.unlocked_at,
        }