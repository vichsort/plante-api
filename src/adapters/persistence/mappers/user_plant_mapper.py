from src.domain.entities.user_plant import UserPlant, IdentificationStatus, IdentificationSource
from src.domain.entities.care_schedule import CareSchedule, CareType
from src.domain.value_objects.care_interval import CareInterval
from src.domain.value_objects.streak import Streak
from src.adapters.persistence.models.user_plant_model import UserPlantModel

class UserPlantMapper:
    @staticmethod
    def to_domain(model: UserPlantModel) -> UserPlant:
        care_schedule = CareSchedule(
            id=model.id,  # CareSchedule não tem id próprio — usa o do UserPlant
            user_plant_id=model.id,
            care_type=CareType(model.care_type),
            interval=CareInterval(days=model.care_interval_days),
            is_active=model.care_is_active,
            created_at=model.care_created_at,
            next_due_at=model.care_next_due_at,
            last_completed_at=model.care_last_completed_at,
            climate_adjusted=model.care_climate_adjusted,
        )
        return UserPlant(
            id=model.id,
            user_id=model.user_id,
            scientific_name=model.scientific_name,
            identification_confidence=model.identification_confidence,
            identification_source=IdentificationSource(model.identification_source),
            status=IdentificationStatus(model.status),
            added_at=model.added_at,
            care_schedule=care_schedule,
            nickname=model.nickname,
            primary_image_url=model.primary_image_url,
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
            scientific_name=entity.scientific_name,
            identification_confidence=entity.identification_confidence,
            identification_source=entity.identification_source.value,
            status=entity.status.value,
            added_at=entity.added_at,
            nickname=entity.nickname,
            primary_image_url=entity.primary_image_url,
            last_watered_at=entity.last_watered_at,
            streak_count=entity.watering_streak.current_count,
            streak_last_action_time=entity.watering_streak.last_action_time,
            care_type=cs.care_type.value,
            care_interval_days=cs.interval.days,
            care_is_active=cs.is_active,
            care_next_due_at=cs.next_due_at,
            care_last_completed_at=cs.last_completed_at,
            care_climate_adjusted=cs.climate_adjusted,
            care_created_at=cs.created_at,
        )