from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.user_plant import UserPlant
from src.domain.ports.user_plant_repository import IUserPlantRepository
from src.adapters.persistence.models.user_plant_model import UserPlantModel
from src.adapters.persistence.mappers.user_plant_mapper import UserPlantMapper

class UserPlantRepository(IUserPlantRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user_plant: UserPlant) -> UserPlant:
        model = UserPlantMapper.to_model(user_plant)
        self._session.add(model)
        await self._session.flush()
        return UserPlantMapper.to_domain(model)

    async def get_by_id(self, user_plant_id: int, user_id: int) -> UserPlant | None:
        stmt = (
            select(UserPlantModel)
            .where(UserPlantModel.id == user_plant_id)
            .where(UserPlantModel.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return UserPlantMapper.to_domain(model) if model else None

    async def list_by_user(self, user_id: int) -> list[UserPlant]:
        stmt = select(UserPlantModel).where(UserPlantModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return [UserPlantMapper.to_domain(m) for m in result.scalars().all()]

    async def delete(self, user_plant_id: int, user_id: int) -> bool:
        stmt = (
            delete(UserPlantModel)
            .where(UserPlantModel.id == user_plant_id)
            .where(UserPlantModel.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def count_by_user(self, user_id: int) -> int:
        stmt = select(func.count()).where(UserPlantModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()