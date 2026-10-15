from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.persistence.repositories.achievement_repository import (
    AchievementRepository,
)
from src.adapters.persistence.repositories.health_identification_sample_repository import (
    HealthIdentificationSampleRepository,
)
from src.adapters.persistence.repositories.health_record_repository import (
    HealthRecordRepository,
)
from src.adapters.persistence.repositories.identification_sample_repository import (
    IdentificationSampleRepository,
)
from src.adapters.persistence.repositories.plant_nutritional_repository import (
    PlantNutritionalRepository,
)
from src.adapters.persistence.repositories.plant_reference_image_repository import (
    PlantReferenceImageRepository,
)
from src.adapters.persistence.repositories.plant_species_repository import (
    PlantSpeciesRepository,
)
from src.adapters.persistence.repositories.user_plant_repository import (
    UserPlantRepository,
)
from src.adapters.persistence.repositories.user_repository import UserRepository
from src.domain.ports.unit_of_work import IUnitOfWork


class SqlAlchemyUnitOfWork(IUnitOfWork):
    """Uma `AsyncSession` por bloco `async with`; os repositórios do bloco usam essa sessão."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("Unit of work already open: nested `async with` is not supported.")
        session = self._session_factory()
        self._session = session
        self.users = UserRepository(session)
        self.user_plants = UserPlantRepository(session)
        self.species = PlantSpeciesRepository(session)
        self.nutritional = PlantNutritionalRepository(session)
        self.reference_images = PlantReferenceImageRepository(session)
        self.identification_samples = IdentificationSampleRepository(session)
        self.health_records = HealthRecordRepository(session)
        self.health_samples = HealthIdentificationSampleRepository(session)
        self.achievements = AchievementRepository(session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session, self._session = self._session, None
        if session is None:
            return
        try:
            await session.rollback()  # sem efeito depois de um commit
        finally:
            await session.close()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work is not open.")
        await self._session.commit()
