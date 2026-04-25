from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.health_identification_sample import (
    HealthIdentificationSample,
    HealthSampleStatus,
)
from src.domain.ports.health_identification_sample_repository import (
    IHealthIdentificationSampleRepository,
)
from src.adapters.persistence.mappers.health_identification_sample_mapper import (
    HealthIdentificationSampleMapper,
)
from src.adapters.persistence.models.health_identification_sample_model import (
    HealthIdentificationSampleModel,
)

class HealthIdentificationSampleRepository(IHealthIdentificationSampleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        sample: HealthIdentificationSample,
    ) -> HealthIdentificationSample:
        model = HealthIdentificationSampleMapper.to_model(sample)
        self._session.add(model)
        await self._session.flush()
        return HealthIdentificationSampleMapper.to_domain(model)

    async def get_by_health_record_id(
        self,
        health_record_id: int,
    ) -> HealthIdentificationSample | None:
        stmt = select(HealthIdentificationSampleModel).where(
            HealthIdentificationSampleModel.health_record_id == health_record_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return HealthIdentificationSampleMapper.to_domain(model) if model else None

    async def get_confirmed_before(
        self,
        cutoff: datetime,
    ) -> list[HealthIdentificationSample]:
        stmt = (
            select(HealthIdentificationSampleModel)
            .where(
                HealthIdentificationSampleModel.status == HealthSampleStatus.CONFIRMED.value,
                HealthIdentificationSampleModel.confirmed_at <= cutoff,
                HealthIdentificationSampleModel.user_id.is_not(None),
            )
        )
        result = await self._session.execute(stmt)
        return [
            HealthIdentificationSampleMapper.to_domain(m)
            for m in result.scalars().all()
        ]

    async def list_by_scientific_name(
        self,
        scientific_name: str,
        limit: int = 100,
    ) -> list[HealthIdentificationSample]:
    # IMPORTANTE QUE AQUI filtramos se o status tá como confirmado, o que 
    # não é necessário mas pro treinamento da IA vai ser positivo (no longo prazo, espero)
    # quando eu conseguir uma avaliação a respeito disso, modifico (se necessário). Por enquanto,
    # prefiro ter aqui meio que como uma cláusula de segurança.
        stmt = (
            select(HealthIdentificationSampleModel)
            .where(
                HealthIdentificationSampleModel.scientific_name == scientific_name,
                HealthIdentificationSampleModel.status == HealthSampleStatus.CONFIRMED.value,
            )
            .order_by(HealthIdentificationSampleModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [
            HealthIdentificationSampleMapper.to_domain(m)
            for m in result.scalars().all()
        ]