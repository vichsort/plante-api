"""Dublês do achievements para os testes daqui: o repositório e o UoW em memória."""
from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import uuid4

from src.modules.achievements.domain.ports.achievement_repository import (
    AchievementView,
    IAchievementRepository,
)
from src.modules.achievements.domain.ports.unit_of_work import IAchievementsUnitOfWork
from src.modules.achievements.domain.value_objects.ids import AchievementId
from src.shared.domain import UserId


def make_achievement(badge_code: str = "first_plant") -> AchievementView:
    return AchievementView(id=AchievementId(uuid4()), badge_code=badge_code, unlocked_at=datetime.now(UTC))


class InMemoryAchievementRepository(IAchievementRepository):
    """Conquistas desbloqueadas por usuário."""

    def __init__(self, unlocked: dict[UserId, list[AchievementView]] | None = None) -> None:
        self.unlocked = unlocked or {}

    async def get_user_achievements_view(self, user_id: UserId) -> list[AchievementView]:
        return list(self.unlocked.get(user_id, []))


class FakeAchievementsUnitOfWork(IAchievementsUnitOfWork):
    def __init__(self, achievements: InMemoryAchievementRepository | None = None) -> None:
        self.achievements: InMemoryAchievementRepository = achievements or InMemoryAchievementRepository()
        self.opened = 0
        self.commits = 0

    @property
    def joined(self) -> bool:
        return False

    async def __aenter__(self) -> Self:
        self.opened += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1
