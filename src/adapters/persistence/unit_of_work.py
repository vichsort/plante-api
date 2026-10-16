from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.repositories.achievement_repository import (
    AchievementRepository,
)
from src.adapters.persistence.repositories.health_record_repository import (
    HealthRecordRepository,
)
from src.adapters.persistence.repositories.identification_repository import (
    IdentificationRepository,
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
from src.shared.adapters import SqlAlchemyUnitOfWork as BaseUnitOfWork


class SqlAlchemyUnitOfWork(BaseUnitOfWork, IUnitOfWork):
    """UoW do código em camadas antigo: todos os repositórios que ainda não foram para um módulo."""

    def _bind(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)
        self.user_plants = UserPlantRepository(session)
        self.species = PlantSpeciesRepository(session)
        self.nutritional = PlantNutritionalRepository(session)
        self.reference_images = PlantReferenceImageRepository(session)
        self.identifications = IdentificationRepository(session)
        self.health_records = HealthRecordRepository(session)
        self.achievements = AchievementRepository(session)
