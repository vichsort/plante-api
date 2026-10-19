from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identification.adapters.persistence.repositories.identification import (
    IdentificationRepository,
)
from src.modules.identification.domain.ports.unit_of_work import (
    IIdentificationUnitOfWork,
)
from src.shared.adapters import SqlAlchemyUnitOfWork


class SqlAlchemyIdentificationUnitOfWork(SqlAlchemyUnitOfWork, IIdentificationUnitOfWork):
    def _bind(self, session: AsyncSession) -> None:
        self.identifications = IdentificationRepository(session)
