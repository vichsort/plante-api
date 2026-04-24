from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.domain.entities.plant_identification_sample import PlantIdentificationSample, SampleStatus
from src.domain.ports.identification_sample_repository import IIdentificationSampleRepository
from src.adapters.persistence.models.plant_identification_sample_model import PlantIdentificationSampleModel
from src.adapters.persistence.mappers.identification_sample_mapper import IdentificationSampleMapper

class IdentificationSampleRepository(IIdentificationSampleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, sample: PlantIdentificationSample) -> PlantIdentificationSample:
        model = IdentificationSampleMapper.to_model(sample)
        self._session.add(model)
        await self._session.flush()
        return IdentificationSampleMapper.to_domain(model)

    async def get_by_id(self, sample_id: int) -> PlantIdentificationSample | None:
        result = await self._session.get(PlantIdentificationSampleModel, sample_id)
        return IdentificationSampleMapper.to_domain(result) if result else None

    async def get_pending_by_user(self, user_id: int) -> list[PlantIdentificationSample]:
        stmt = (
            select(PlantIdentificationSampleModel)
            .where(PlantIdentificationSampleModel.user_id == user_id)
            .where(PlantIdentificationSampleModel.status == SampleStatus.PENDING.value)
        )
        result = await self._session.execute(stmt)
        return [IdentificationSampleMapper.to_domain(m) for m in result.scalars().all()]

    async def get_complete_for_training(self, limit: int = 100) -> list[PlantIdentificationSample]:
        stmt = (
            select(PlantIdentificationSampleModel)
            .where(PlantIdentificationSampleModel.status == SampleStatus.CONFIRMED.value)
            .where(PlantIdentificationSampleModel.has_deep_analysis.is_(True))
            .where(PlantIdentificationSampleModel.has_nutritional_analysis.is_(True))
            .where(PlantIdentificationSampleModel.user_id.is_(None)) # já anonimizado
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [IdentificationSampleMapper.to_domain(m) for m in result.scalars().all()]

    async def get_confirmed_before(self, cutoff: datetime) -> list[PlantIdentificationSample]:
        stmt = (
            select(PlantIdentificationSampleModel)
            .where(PlantIdentificationSampleModel.status == SampleStatus.CONFIRMED.value)
            .where(PlantIdentificationSampleModel.confirmed_at < cutoff)
            .where(PlantIdentificationSampleModel.user_id.isnot(None)) # ainda não anonimizado
        )
        result = await self._session.execute(stmt)
        return [IdentificationSampleMapper.to_domain(m) for m in result.scalars().all()]