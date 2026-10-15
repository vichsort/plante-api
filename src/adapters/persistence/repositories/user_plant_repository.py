from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.persistence.mappers.user_plant_mapper import UserPlantMapper
from src.adapters.persistence.models.plant_species_model import PlantSpeciesModel
from src.adapters.persistence.models.user_plant_model import UserPlantModel
from src.domain.entities.user_plant import UserPlant
from src.domain.ports.user_plant_repository import IUserPlantRepository


class UserPlantRepository(IUserPlantRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user_plant: UserPlant) -> UserPlant:
        model = UserPlantMapper.to_model(user_plant)
        # merge: INSERT para entidade nova, UPDATE para existente (add sempre tentaria INSERT)
        model = await self._session.merge(model)
        await self._session.flush()
        return UserPlantMapper.to_domain(model)

    async def get_by_id(self, user_plant_id: Any, user_id: Any | None = None) -> UserPlant | None:
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

    async def list_by_user(self, user_id: Any) -> list[UserPlant]:
        stmt = (
            select(UserPlantModel)
            .where(UserPlantModel.user_id == user_id)
            .where(UserPlantModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return [UserPlantMapper.to_domain(m) for m in result.scalars().all()]

    async def delete(self, user_plant_id: Any, user_id: Any) -> bool:
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

    async def count_by_user(self, user_id: Any) -> int:
        stmt = (
            select(func.count())
            .where(UserPlantModel.user_id == user_id)
            .where(UserPlantModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_garden_view_for_user(self, user_id: Any) -> list[dict[str, Any]]:
        stmt = (
            select(UserPlantModel)
            .where(UserPlantModel.user_id == user_id)
            .where(UserPlantModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        items = []
        for m in models:
            domain = UserPlantMapper.to_domain(m)
            items.append({
                "id": str(domain.id) if domain.id else None,
                "scientific_name": domain.scientific_name,
                "nickname": domain.nickname,
                "display_name": domain.display_name,
                "primary_image_url": domain.primary_image_url,
                "last_watered_at": domain.last_watered_at.isoformat() if domain.last_watered_at else None,
                "next_due_at": domain.care_schedule.next_due_at.isoformat() if domain.care_schedule.next_due_at else None,
                "needs_watering": domain.needs_watering,
                "streak_count": domain.watering_streak.current_count,
            })
        return items

    async def get_plant_details_view(self, user_plant_id: Any, user_id: Any) -> dict[str, Any] | None:
        stmt = (
            select(UserPlantModel, PlantSpeciesModel)
            .outerjoin(PlantSpeciesModel, UserPlantModel.scientific_name == PlantSpeciesModel.scientific_name)
            .where(UserPlantModel.id == user_plant_id)
            .where(UserPlantModel.user_id == user_id)
            .where(UserPlantModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        row = result.first()
        if not row:
            return None

        user_plant_model, species_model = row
        domain = UserPlantMapper.to_domain(user_plant_model)

        return {
            "id": str(domain.id) if domain.id else None,
            "user_id": str(domain.user_id) if domain.user_id else None,
            "scientific_name": domain.scientific_name,
            "nickname": domain.nickname,
            "display_name": domain.display_name,
            "primary_image_url": domain.primary_image_url,
            "identification_confidence": domain.identification_confidence,
            "identification_source": domain.identification_source.value if hasattr(domain.identification_source, "value") else str(domain.identification_source),
            "status": domain.status.value if hasattr(domain.status, "value") else str(domain.status),
            "added_at": domain.added_at.isoformat() if domain.added_at else None,
            "last_watered_at": domain.last_watered_at.isoformat() if domain.last_watered_at else None,
            "needs_watering": domain.needs_watering,
            "watering_streak": domain.watering_streak.current_count,
            "care_schedule": {
                "care_type": domain.care_schedule.care_type.value if hasattr(domain.care_schedule.care_type, "value") else str(domain.care_schedule.care_type),
                "interval_days": domain.care_schedule.interval.days,
                "is_active": domain.care_schedule.is_active,
                "next_due_at": domain.care_schedule.next_due_at.isoformat() if domain.care_schedule.next_due_at else None,
            },
            "species_info": {
                "family": species_model.family if species_model else None,
                "genus": species_model.genus if species_model else None,
                "common_names": species_model.common_names if species_model else [],
                "is_edible": species_model.is_edible if species_model else None,
                "water_frequency_per_week": species_model.water_frequency_per_week if species_model else None,
                "light_requirement": species_model.light_requirement if species_model else None,
                "soil_type": species_model.soil_type if species_model else None,
                "habitat": species_model.habitat if species_model else None,
            } if species_model else None,
        }

    async def get_overdue_plants(self, current_time: datetime) -> list[UserPlant]:
        stmt = (
            select(UserPlantModel)
            .where(UserPlantModel.care_next_due_at < current_time)
            .where(UserPlantModel.deleted_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return [UserPlantMapper.to_domain(m) for m in result.scalars().all()]