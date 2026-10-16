from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.adapters.persistence.repositories.user import UserRepository
from src.modules.identity.domain.ports.unit_of_work import IIdentityUnitOfWork
from src.shared.adapters import SqlAlchemyUnitOfWork


class SqlAlchemyIdentityUnitOfWork(SqlAlchemyUnitOfWork, IIdentityUnitOfWork):
    def _bind(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)
