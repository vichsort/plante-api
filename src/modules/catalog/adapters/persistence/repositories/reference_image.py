from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.adapters.persistence.mappers.reference_image import (
    PlantReferenceImageMapper,
)
from src.modules.catalog.adapters.persistence.models.reference_image import (
    PlantReferenceImageModel,
)
from src.modules.catalog.domain.entities.reference_image import PlantReferenceImage
from src.modules.catalog.domain.ports.reference_image_repository import (
    IPlantReferenceImageRepository,
)


class PlantReferenceImageRepository(IPlantReferenceImageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, image: PlantReferenceImage) -> PlantReferenceImage:
        model = PlantReferenceImageMapper.to_model(image)
        # merge: INSERT para entidade nova, UPDATE para existente (add sempre tentaria INSERT)
        model = await self._session.merge(model)
        await self._session.flush()
        return PlantReferenceImageMapper.to_domain(model)

    async def get_by_scientific_name(self, scientific_name: str) -> list[PlantReferenceImage]:
        stmt = (
            select(PlantReferenceImageModel)
            .where(PlantReferenceImageModel.scientific_name == scientific_name)
        )
        result = await self._session.execute(stmt)
        return [PlantReferenceImageMapper.to_domain(m) for m in result.scalars().all()]