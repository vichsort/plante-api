from src.adapters.persistence.mappers.sources import to_health_source
from src.adapters.persistence.models.health_record_model import HealthRecordModel
from src.domain.entities.health_record import HealthRecord
from src.domain.value_objects.ids import (
    HealthRecordId,
    TrainingHealthSampleId,
    UserId,
    UserPlantId,
)


class HealthRecordMapper:
    @staticmethod
    def to_domain(model: HealthRecordModel) -> HealthRecord:
        return HealthRecord(
            id=HealthRecordId(model.id),
            user_plant_id=UserPlantId(model.user_plant_id),
            user_id=UserId(model.user_id) if model.user_id else None,
            scientific_name=model.scientific_name,
            diagnosed_at=model.diagnosed_at,
            vitality_score=model.vitality_score,
            severity=model.severity,
            source=to_health_source(model.source),
            image_key=model.image_key or "",
            training_sample_id=TrainingHealthSampleId(model.training_sample_id),
            issues_detected=tuple(model.issues_detected or []),
            treatment_plan=tuple(model.treatment_plan or []),
            recovery_estimate_days=model.recovery_estimate_days,
            notes=model.notes,
        )

    @staticmethod
    def to_model(domain: HealthRecord) -> HealthRecordModel:
        return HealthRecordModel(
            id=domain.id,
            user_plant_id=domain.user_plant_id,
            user_id=domain.user_id,
            scientific_name=domain.scientific_name,
            diagnosed_at=domain.diagnosed_at,
            vitality_score=domain.vitality_score,
            severity=domain.severity,
            source=domain.source,
            image_key=domain.image_key,
            training_sample_id=domain.training_sample_id,
            issues_detected=list(domain.issues_detected),
            treatment_plan=list(domain.treatment_plan),
            recovery_estimate_days=domain.recovery_estimate_days,
            notes=domain.notes,
        )