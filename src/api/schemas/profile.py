from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.ports.achievement_repository import AchievementView


class AchievementItemResponse(BaseModel):
    id: UUID
    badge_code: str
    unlocked_at: datetime

    @classmethod
    def from_domain(cls, achievement: AchievementView) -> "AchievementItemResponse":
        return cls(
            id=achievement.id,
            badge_code=achievement.badge_code,
            unlocked_at=achievement.unlocked_at,
        )