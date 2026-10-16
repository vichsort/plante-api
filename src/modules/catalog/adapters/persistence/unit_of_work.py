from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.adapters.persistence.repositories.nutritional import (
    PlantNutritionalRepository,
)
from src.modules.catalog.adapters.persistence.repositories.plant_species import (
    PlantSpeciesRepository,
)
from src.modules.catalog.adapters.persistence.repositories.reference_image import (
    PlantReferenceImageRepository,
)
from src.modules.catalog.domain.ports.unit_of_work import ICatalogUnitOfWork
from src.shared.adapters import SqlAlchemyUnitOfWork


class SqlAlchemyCatalogUnitOfWork(SqlAlchemyUnitOfWork, ICatalogUnitOfWork):
    def _bind(self, session: AsyncSession) -> None:
        self.species = PlantSpeciesRepository(session)
        self.reference_images = PlantReferenceImageRepository(session)
        self.nutritional = PlantNutritionalRepository(session)
