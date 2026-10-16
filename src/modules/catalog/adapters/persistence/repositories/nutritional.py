from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.adapters.persistence.mappers.nutritional import (
    PlantNutritionalMapper,
)
from src.modules.catalog.adapters.persistence.models.nutritional import (
    PlantNutritionalModel,
)
from src.modules.catalog.domain.entities.nutritional import PlantNutritional
from src.modules.catalog.domain.ports.nutritional_repository import (
    IPlantNutritionalRepository,
)


class PlantNutritionalRepository(IPlantNutritionalRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, nutritional: PlantNutritional) -> PlantNutritional:
        model = PlantNutritionalMapper.to_model(nutritional)
        # merge: INSERT para entidade nova, UPDATE para existente (add sempre tentaria INSERT)
        model = await self._session.merge(model)
        await self._session.flush()
        return PlantNutritionalMapper.to_domain(model)

    async def get_by_scientific_name(self, scientific_name: str) -> PlantNutritional | None:
        result = await self._session.get(PlantNutritionalModel, scientific_name)
        return PlantNutritionalMapper.to_domain(result) if result else None