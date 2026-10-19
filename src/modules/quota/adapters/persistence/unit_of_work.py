from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.quota.adapters.persistence.repositories.quota import (
    QuotaRepository,
)
from src.modules.quota.domain.ports.unit_of_work import IQuotaUnitOfWork
from src.shared.adapters import SqlAlchemyUnitOfWork


class SqlAlchemyQuotaUnitOfWork(SqlAlchemyUnitOfWork, IQuotaUnitOfWork):
    def _bind(self, session: AsyncSession) -> None:
        self.quotas = QuotaRepository(session)
