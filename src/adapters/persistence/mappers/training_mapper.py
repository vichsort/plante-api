from pydantic import TypeAdapter

from src.adapters.persistence.mappers.sources import (
    to_health_source,
    to_identification_origin,
)
from src.adapters.persistence.models import (
    TrainingFeedbackModel,
    TrainingHealthSampleModel,
    TrainingIdentificationSampleModel,
)
from src.domain.entities.training import (
    TrainingFeedback,
    TrainingHealthSample,
    TrainingIdentificationSample,
)
from src.domain.value_objects.ids import (
    TrainingFeedbackId,
    TrainingHealthSampleId,
    TrainingIdentificationSampleId,
)
from src.domain.value_objects.json_value import JsonValue
from src.domain.value_objects.provider_signals import (
    HealthSignals,
    IdentificationSignals,
)
from src.domain.value_objects.training_location import TrainingLocation

# Sinais ficam numa coluna JSON; a leitura é validada contra as dataclasses do domínio
_IDENTIFICATION_SIGNALS = TypeAdapter(tuple[IdentificationSignals, ...])
_HEALTH_SIGNALS = TypeAdapter(HealthSignals)
_JSON: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)


def _location(model: TrainingIdentificationSampleModel | TrainingHealthSampleModel) -> TrainingLocation:
    return TrainingLocation(
        country=model.country,
        state=model.state,
        grid_latitude=model.grid_latitude,
        grid_longitude=model.grid_longitude,
    )


class TrainingMapper:
    @staticmethod
    def identification_to_model(entity: TrainingIdentificationSample) -> TrainingIdentificationSampleModel:
        return TrainingIdentificationSampleModel(
            id=entity.id,
            image_key=entity.image_key,
            scientific_name=entity.scientific_name,
            family=entity.family,
            genus=entity.genus,
            gbif_id=entity.gbif_id,
            provider_entity_id=entity.provider_entity_id,
            source=entity.source,
            confidence=entity.confidence,
            low_confidence=entity.low_confidence,
            signals=_JSON.validate_python(_IDENTIFICATION_SIGNALS.dump_python(entity.signals, mode="json")),
            period=entity.period,
            country=entity.location.country,
            state=entity.location.state,
            grid_latitude=entity.location.grid_latitude,
            grid_longitude=entity.location.grid_longitude,
        )

    @staticmethod
    def identification_to_domain(model: TrainingIdentificationSampleModel) -> TrainingIdentificationSample:
        return TrainingIdentificationSample(
            id=TrainingIdentificationSampleId(model.id),
            image_key=model.image_key,
            scientific_name=model.scientific_name,
            confidence=model.confidence,
            source=to_identification_origin(model.source),
            low_confidence=model.low_confidence,
            signals=_IDENTIFICATION_SIGNALS.validate_python(model.signals),
            period=model.period,
            location=_location(model),
            family=model.family,
            genus=model.genus,
            gbif_id=model.gbif_id,
            provider_entity_id=model.provider_entity_id,
        )

    @staticmethod
    def health_to_model(entity: TrainingHealthSample) -> TrainingHealthSampleModel:
        return TrainingHealthSampleModel(
            id=entity.id,
            image_key=entity.image_key,
            scientific_name=entity.scientific_name,
            vitality_score=entity.vitality_score,
            severity=entity.severity,
            source=entity.source,
            issues_detected=list(entity.issues_detected),
            treatment_plan=list(entity.treatment_plan),
            reference_image_keys=list(entity.reference_image_keys),
            recovery_estimate_days=entity.recovery_estimate_days,
            notes=entity.notes,
            signals=_JSON.validate_python(_HEALTH_SIGNALS.dump_python(entity.signals, mode="json")),
            period=entity.period,
            country=entity.location.country,
            state=entity.location.state,
            grid_latitude=entity.location.grid_latitude,
            grid_longitude=entity.location.grid_longitude,
        )

    @staticmethod
    def health_to_domain(model: TrainingHealthSampleModel) -> TrainingHealthSample:
        return TrainingHealthSample(
            id=TrainingHealthSampleId(model.id),
            image_key=model.image_key,
            scientific_name=model.scientific_name,
            vitality_score=model.vitality_score,
            severity=model.severity,
            source=to_health_source(model.source),
            signals=_HEALTH_SIGNALS.validate_python(model.signals),
            period=model.period,
            location=_location(model),
            issues_detected=tuple(model.issues_detected),
            treatment_plan=tuple(model.treatment_plan),
            reference_image_keys=tuple(model.reference_image_keys),
            recovery_estimate_days=model.recovery_estimate_days,
            notes=model.notes,
        )

    @staticmethod
    def feedback_to_model(entity: TrainingFeedback) -> TrainingFeedbackModel:
        return TrainingFeedbackModel(
            id=entity.id,
            identification_sample_id=entity.identification_sample_id,
            health_sample_id=entity.health_sample_id,
            verdict=entity.verdict,
            origin=entity.origin,
            suggested_name=entity.suggested_name,
            given_on=entity.given_on,
        )

    @staticmethod
    def feedback_to_domain(model: TrainingFeedbackModel) -> TrainingFeedback:
        return TrainingFeedback(
            id=TrainingFeedbackId(model.id),
            verdict=model.verdict,
            origin=model.origin,
            given_on=model.given_on,
            identification_sample_id=(
                TrainingIdentificationSampleId(model.identification_sample_id)
                if model.identification_sample_id else None
            ),
            health_sample_id=TrainingHealthSampleId(model.health_sample_id) if model.health_sample_id else None,
            suggested_name=model.suggested_name,
        )
