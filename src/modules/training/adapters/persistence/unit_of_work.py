from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.training.adapters.persistence.repositories.training import (
    TrainingRepository,
)
from src.modules.training.domain.ports.unit_of_work import ITrainingUnitOfWork
from src.shared.adapters import SqlAlchemyUnitOfWork


class SqlAlchemyTrainingUnitOfWork(SqlAlchemyUnitOfWork, ITrainingUnitOfWork):
    def _bind(self, session: AsyncSession) -> None:
        self.training = TrainingRepository(session)
