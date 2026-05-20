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
            image_key=model.image_key,
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
            scientific_name=domain.scientific_name,
            diagnosed_at=domain.diagnosed_at,
            vitality_score=domain.vitality_score,
            severity=domain.severity,
            source=domain.source,
            image_key=domain.image_key,
            issues_detected=list(domain.issues_detected),
            treatment_plan=list(domain.treatment_plan),
            recovery_estimate_days=domain.recovery_estimate_days,
            notes=domain.notes,
        )