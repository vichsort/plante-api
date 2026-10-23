from src.modules.garden.adapters.persistence.models.user_plant import UserPlantModel
from src.modules.garden.domain.entities.care_schedule import CareSchedule, CareType
from src.modules.garden.domain.entities.user_plant import (
    UserPlant,
)
from src.modules.garden.domain.value_objects.care_interval import CareInterval
from src.modules.garden.domain.value_objects.ids import UserPlantId
from src.modules.garden.domain.value_objects.streak import Streak
from src.modules.identification import IdentificationId
from src.shared.domain import UserId


class UserPlantMapper:
    @staticmethod
    def to_domain(model: UserPlantModel) -> UserPlant:
        care_schedule = CareSchedule(
            care_type=CareType(model.care_type),
            interval=CareInterval(days=model.care_interval_days),
            is_active=model.care_is_active,
            created_at=model.care_created_at,
            next_due_on=model.care_next_due_on,
            last_completed_at=model.care_last_completed_at,
            climate_adjusted=model.care_climate_adjusted,
        )
        return UserPlant(
            id=UserPlantId(model.id),
            user_id=UserId(model.user_id),
            identification_id=IdentificationId(model.identification_id),
            scientific_name=model.scientific_name,
            identification_confidence=model.identification_confidence,
            identification_source=model.identification_source,
            status=model.status,
            added_at=model.added_at,
            care_schedule=care_schedule,
            nickname=model.nickname,
            primary_image_key=model.primary_image_key,
            last_watered_at=model.last_watered_at,
            watering_streak=Streak(
                current_count=model.streak_count,
                last_action_time=model.streak_last_action_time,
            ),
        )

    @staticmethod
    def to_model(entity: UserPlant) -> UserPlantModel:
        cs = entity.care_schedule
        return UserPlantModel(
            id=entity.id,
            user_id=entity.user_id,
            identification_id=entity.identification_id,
            scientific_name=entity.scientific_name,
            identification_confidence=entity.identification_confidence,
            identification_source=entity.identification_source,
            status=entity.status,
            added_at=entity.added_at,
            nickname=entity.nickname,
            primary_image_key=entity.primary_image_key,
            last_watered_at=entity.last_watered_at,
            streak_count=entity.watering_streak.current_count,
            streak_last_action_time=entity.watering_streak.last_action_time,
            care_type=cs.care_type.value,
            care_interval_days=cs.interval.days,
            care_is_active=cs.is_active,
            care_next_due_on=cs.next_due_on,
            care_last_completed_at=cs.last_completed_at,
            care_climate_adjusted=cs.climate_adjusted,
            care_created_at=cs.created_at,
        )