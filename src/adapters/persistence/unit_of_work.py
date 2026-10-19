from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.repositories.achievement_repository import (
    AchievementRepository,
)
from src.adapters.persistence.repositories.health_record_repository import (
    HealthRecordRepository,
)
from src.domain.ports.unit_of_work import IUnitOfWork
from src.shared.adapters import SqlAlchemyUnitOfWork as BaseUnitOfWork


class SqlAlchemyUnitOfWork(BaseUnitOfWork, IUnitOfWork):
    """UoW do código em camadas antigo: todos os repositórios que ainda não foram para um módulo."""

    def _bind(self, session: AsyncSession) -> None:
        self.health_records = HealthRecordRepository(session)
        self.achievements = AchievementRepository(session)
