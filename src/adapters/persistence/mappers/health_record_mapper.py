from src.domain.entities.health_record import HealthRecord, HealthSeverity
from src.adapters.persistence.models.health_record_model import HealthRecordModel

class HealthRecordMapper:
    @staticmethod
    def to_domain(model: HealthRecordModel) -> HealthRecord:
        return HealthRecord(
            id=model.id,
            user_plant_id=model.user_plant_id,
            scientific_name=model.scientific_name,
            diagnosed_at=model.diagnosed_at,
            vitality_score=model.vitality_score,
            severity=HealthSeverity(model.severity),
            source=model.source,
            issues_detected=tuple(model.issues_detected or []),
            treatment_plan=tuple(model.treatment_plan or []),
            recovery_estimate_days=model.recovery_estimate_days,
            notes=model.notes,
        )

    @staticmethod
    def to_model(entity: HealthRecord) -> HealthRecordModel:
        return HealthRecordModel(
            id=entity.id,
            user_plant_id=entity.user_plant_id,
            scientific_name=entity.scientific_name,
            diagnosed_at=entity.diagnosed_at,
            vitality_score=entity.vitality_score,
            severity=entity.severity.value,
            source=entity.source,
            issues_detected=list(entity.issues_detected),
            treatment_plan=list(entity.treatment_plan),
            recovery_estimate_days=entity.recovery_estimate_days,
            notes=entity.notes,
        )