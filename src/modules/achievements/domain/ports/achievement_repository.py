from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from src.modules.achievements.domain.value_objects.ids import AchievementId
from src.shared.domain import UserId


@dataclass(frozen=True)
class AchievementView:
    id: AchievementId
    badge_code: str
    unlocked_at: datetime


class IAchievementRepository(ABC):
    """As conquistas (badges) desbloqueadas pelos usuários."""

    @abstractmethod
    async def get_user_achievements_view(self, user_id: UserId) -> list[AchievementView]:
        """Medalhas desbloqueadas pelo usuário."""
        ...
