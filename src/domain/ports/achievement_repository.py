from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from src.domain.value_objects.ids import AchievementId, UserId


@dataclass(frozen=True)
class AchievementView:
    id: AchievementId
    badge_code: str
    unlocked_at: datetime


class IAchievementRepository(ABC):
    """
    Porta para gerenciar e consultar as conquistas (badges) dos usuários.
    """

    @abstractmethod
    async def get_user_achievements_view(self, user_id: UserId) -> list[AchievementView]:
        """Medalhas desbloqueadas pelo usuário."""
        ...

    @abstractmethod
    async def grant_badge(self, user_id: UserId, badge_code: str) -> None:
        ...
