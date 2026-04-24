from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.plant_nutritional import PlantNutritional
from src.domain.ports.plant_nutritional_repository import IPlantNutritionalRepository
from src.adapters.persistence.models.plant_nutritional_model import PlantNutritionalModel
from src.adapters.persistence.mappers.plant_nutritional_mapper import PlantNutritionalMapper

class PlantNutritionalRepository(IPlantNutritionalRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, nutritional: PlantNutritional) -> PlantNutritional:
        model = PlantNutritionalMapper.to_model(nutritional)
        self._session.add(model)
        await self._session.flush()
        return PlantNutritionalMapper.to_domain(model)

    async def get_by_scientific_name(self, scientific_name: str) -> PlantNutritional | None:
        result = await self._session.get(PlantNutritionalModel, scientific_name)
        return PlantNutritionalMapper.to_domain(result) if result else None