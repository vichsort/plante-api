from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.mappers.plant_species_mapper import PlantSpeciesMapper
from src.adapters.persistence.mappers.user_plant_mapper import UserPlantMapper
from src.adapters.persistence.models.plant_species_model import PlantSpeciesModel
from src.adapters.persistence.models.user_plant_model import UserPlantModel
from src.domain.entities.user_plant import UserPlant
from src.domain.ports.user_plant_repository import IUserPlantRepository, PlantDetails
from src.domain.value_objects.ids import IdentificationId, UserPlantId
from src.shared.domain import UserId


class UserPlantRepository(IUserPlantRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user_plant: UserPlant) -> UserPlant:
        model = UserPlantMapper.to_model(user_plant)
        # merge: INSERT para entidade nova, UPDATE para existente (add sempre tentaria INSERT)
        model = await self._session.merge(model)
        await self._session.flush()
        return UserPlantMapper.to_domain(model)

    async def get_by_id(self, user_plant_id: UserPlantId, user_id: UserId | None = None) -> UserPlant | None:
        stmt = (
            select(UserPlantModel)
            .where(UserPlantModel.id == user_plant_id)
            .where(UserPlantModel.deleted_at.is_(None))
        )
        if user_id is not None:
            stmt = stmt.where(UserPlantModel.user_id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return UserPlantMapper.to_domain(model) if model else None

    async def list_by_user(self, user_id: UserId) -> list[UserPlant]:
        stmt = (
            select(UserPlantModel)
            .where(UserPlantModel.user_id == user_id)
            .where(UserPlantModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return [UserPlantMapper.to_domain(m) for m in result.scalars().all()]

    async def delete(self, user_plant_id: UserPlantId, user_id: UserId) -> bool:
        stmt = (
            select(UserPlantModel)
            .where(UserPlantModel.id == user_plant_id)
            .where(UserPlantModel.user_id == user_id)
            .where(UserPlantModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.deleted_at = datetime.now(UTC)
            await self._session.flush()
            return True
        return False

    async def get_by_identification(self, identification_id: IdentificationId, user_id: UserId) -> UserPlant | None:
        stmt = (
            select(UserPlantModel)
            .where(UserPlantModel.identification_id == identification_id)
            .where(UserPlantModel.user_id == user_id)
            .where(UserPlantModel.deleted_at.is_(None))
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return UserPlantMapper.to_domain(model) if model else None

    async def count_by_user(self, user_id: UserId) -> int:
        stmt = (
            select(func.count())
            .where(UserPlantModel.user_id == user_id)
            .where(UserPlantModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_details(self, user_plant_id: UserPlantId, user_id: UserId) -> PlantDetails | None:
        stmt = (
            select(UserPlantModel, PlantSpeciesModel)
            .outerjoin(PlantSpeciesModel, UserPlantModel.scientific_name == PlantSpeciesModel.scientific_name)
            .where(UserPlantModel.id == user_plant_id)
            .where(UserPlantModel.user_id == user_id)
            .where(UserPlantModel.deleted_at.is_(None))
        )
        row = (await self._session.execute(stmt)).tuples().first()
        if row is None:
            return None

        user_plant_model, species_model = row
        return PlantDetails(
            plant=UserPlantMapper.to_domain(user_plant_model),
            species=PlantSpeciesMapper.to_domain(species_model) if species_model else None,
        )

    async def list_with_streak_due_before(self, due_before: date) -> list[UserPlant]:
        stmt = (
            select(UserPlantModel)
            .where(UserPlantModel.care_next_due_on < due_before)
            .where(UserPlantModel.streak_count > 0)
            .where(UserPlantModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return [UserPlantMapper.to_domain(m) for m in result.scalars().all()]