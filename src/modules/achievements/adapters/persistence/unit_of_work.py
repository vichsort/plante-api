from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.achievements.adapters.persistence.repositories.achievement import (
    AchievementRepository,
)
from src.modules.achievements.domain.ports.unit_of_work import IAchievementsUnitOfWork
from src.shared.adapters import SqlAlchemyUnitOfWork


class SqlAlchemyAchievementsUnitOfWork(SqlAlchemyUnitOfWork, IAchievementsUnitOfWork):
    def _bind(self, session: AsyncSession) -> None:
        self.achievements = AchievementRepository(session)
