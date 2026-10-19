from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.garden.adapters.persistence.repositories.user_plant import (
    UserPlantRepository,
)
from src.modules.garden.domain.ports.unit_of_work import IGardenUnitOfWork
from src.shared.adapters import SqlAlchemyUnitOfWork


class SqlAlchemyGardenUnitOfWork(SqlAlchemyUnitOfWork, IGardenUnitOfWork):
    def _bind(self, session: AsyncSession) -> None:
        self.user_plants = UserPlantRepository(session)
