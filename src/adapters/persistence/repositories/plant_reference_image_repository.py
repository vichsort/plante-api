from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.plant_reference_image import PlantReferenceImage
from src.domain.ports.plant_reference_image_repository import IPlantReferenceImageRepository
from src.adapters.persistence.models.plant_reference_image_model import PlantReferenceImageModel
from src.adapters.persistence.mappers.plant_reference_image_mapper import PlantReferenceImageMapper

class PlantReferenceImageRepository(IPlantReferenceImageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, image: PlantReferenceImage) -> PlantReferenceImage:
        model = PlantReferenceImageMapper.to_model(image)
        self._session.add(model)
        await self._session.flush()
        return PlantReferenceImageMapper.to_domain(model)

    async def get_by_scientific_name(self, scientific_name: str) -> list[PlantReferenceImage]:
        stmt = (
            select(PlantReferenceImageModel)
            .where(PlantReferenceImageModel.scientific_name == scientific_name)
        )
        result = await self._session.execute(stmt)
        return [PlantReferenceImageMapper.to_domain(m) for m in result.scalars().all()]