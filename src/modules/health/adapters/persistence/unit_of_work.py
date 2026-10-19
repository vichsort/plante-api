from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.health.adapters.persistence.repositories.health_record import (
    HealthRecordRepository,
)
from src.modules.health.domain.ports.unit_of_work import IHealthUnitOfWork
from src.shared.adapters import SqlAlchemyUnitOfWork


class SqlAlchemyHealthUnitOfWork(SqlAlchemyUnitOfWork, IHealthUnitOfWork):
    def _bind(self, session: AsyncSession) -> None:
        self.health_records = HealthRecordRepository(session)
