from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.garden import UserPlantId
from src.modules.health.adapters.persistence.mappers.health_record import (
    HealthRecordMapper,
)
from src.modules.health.adapters.persistence.models.health_record import (
    HealthRecordModel,
)
from src.modules.health.domain.entities.health_record import HealthRecord
from src.modules.health.domain.ports.health_record_repository import (
    IHealthRecordRepository,
)
from src.modules.health.domain.value_objects.ids import HealthRecordId
from src.shared.domain import UserId


class HealthRecordRepository(IHealthRecordRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: HealthRecord) -> HealthRecord:
        model = HealthRecordMapper.to_model(record)
        # merge: INSERT para entidade nova, UPDATE para existente (add sempre tentaria INSERT)
        model = await self._session.merge(model)
        await self._session.flush()
        return HealthRecordMapper.to_domain(model)

    async def get_for_user(self, record_id: HealthRecordId, user_id: UserId) -> HealthRecord | None:
        stmt = (
            select(HealthRecordModel)
            .where(HealthRecordModel.id == record_id)
            .where(HealthRecordModel.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return HealthRecordMapper.to_domain(model) if model else None

    async def list_by_plant(self, user_plant_id: UserPlantId, limit: int = 20) -> list[HealthRecord]:
        stmt = (
            select(HealthRecordModel)
            .where(HealthRecordModel.user_plant_id == user_plant_id)
            .order_by(HealthRecordModel.diagnosed_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [HealthRecordMapper.to_domain(m) for m in result.scalars().all()]