from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.health_record import HealthRecord
from src.domain.ports.health_record_repository import IHealthRecordRepository
from src.adapters.persistence.models.health_record_model import HealthRecordModel
from src.adapters.persistence.mappers.health_record_mapper import HealthRecordMapper

class HealthRecordRepository(IHealthRecordRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: HealthRecord) -> HealthRecord:
        model = HealthRecordMapper.to_model(record)
        self._session.add(model)
        await self._session.flush()
        return HealthRecordMapper.to_domain(model)

    async def get_latest_by_plant(self, user_plant_id: int) -> HealthRecord | None:
        stmt = (
            select(HealthRecordModel)
            .where(HealthRecordModel.user_plant_id == user_plant_id)
            .order_by(HealthRecordModel.diagnosed_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return HealthRecordMapper.to_domain(model) if model else None

    async def list_by_plant(self, user_plant_id: int, limit: int = 20) -> list[HealthRecord]:
        stmt = (
            select(HealthRecordModel)
            .where(HealthRecordModel.user_plant_id == user_plant_id)
            .order_by(HealthRecordModel.diagnosed_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [HealthRecordMapper.to_domain(m) for m in result.scalars().all()]