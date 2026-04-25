from src.domain.entities.health_identification_sample import (
    HealthIdentificationSample,
    HealthSampleStatus,
)
from src.adapters.persistence.models.health_identification_sample_model import (
    HealthIdentificationSampleModel,
)

class HealthIdentificationSampleMapper:
    @staticmethod
    def to_domain(model: HealthIdentificationSampleModel) -> HealthIdentificationSample:
        return HealthIdentificationSample(
            id=model.id,
            health_record_id=model.health_record_id,
            scientific_name=model.scientific_name,
            user_image_key=model.user_image_key,
            reference_image_keys=tuple(model.reference_image_keys or []),
            vitality_score=model.vitality_score,
            issues_detected=tuple(model.issues_detected or []),
            treatment_plan=tuple(model.treatment_plan or []),
            identification_source=model.identification_source,
            raw_response=model.raw_response,
            status=HealthSampleStatus(model.status),
            created_at=model.created_at,
            user_id=model.user_id,
            confirmed_at=model.confirmed_at,
            rejected_at=model.rejected_at,
            recovery_estimate_days=model.recovery_estimate_days,
            notes=model.notes,
        )

    @staticmethod
    def to_model(entity: HealthIdentificationSample) -> HealthIdentificationSampleModel:
        return HealthIdentificationSampleModel(
            id=entity.id,
            health_record_id=entity.health_record_id,
            scientific_name=entity.scientific_name,
            user_image_key=entity.user_image_key,
            reference_image_keys=list(entity.reference_image_keys),
            vitality_score=entity.vitality_score,
            issues_detected=list(entity.issues_detected),
            treatment_plan=list(entity.treatment_plan),
            identification_source=entity.identification_source,
            raw_response=entity.raw_response,
            status=entity.status.value,
            created_at=entity.created_at,
            user_id=entity.user_id,
            confirmed_at=entity.confirmed_at,
            rejected_at=entity.rejected_at,
            recovery_estimate_days=entity.recovery_estimate_days,
            notes=entity.notes,
        )