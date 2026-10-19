from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.mappers.identification_mapper import IdentificationMapper
from src.adapters.persistence.models import IdentificationModel
from src.domain.entities.identification import Identification
from src.domain.ports.identification_repository import IIdentificationRepository
from src.domain.value_objects.ids import IdentificationId
from src.shared.domain import UserId


class IdentificationRepository(IIdentificationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, identification: Identification) -> Identification:
        model = await self._session.merge(IdentificationMapper.to_model(identification))
        await self._session.flush()
        return IdentificationMapper.to_domain(model)

    async def get_for_user(self, identification_id: IdentificationId, user_id: UserId) -> Identification | None:
        stmt = (
            select(IdentificationModel)
            .where(IdentificationModel.id == identification_id)
            .where(IdentificationModel.user_id == user_id)
            .where(IdentificationModel.deleted_at.is_(None))
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return IdentificationMapper.to_domain(model) if model else None
