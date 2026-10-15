from src.adapters.persistence.mappers.sources import to_identification_origin
from src.adapters.persistence.models import IdentificationModel
from src.domain.entities.identification import Identification
from src.domain.value_objects.ids import (
    IdentificationId,
    PlantSpeciesId,
    TrainingIdentificationSampleId,
    UserId,
)


class IdentificationMapper:
    @staticmethod
    def to_domain(model: IdentificationModel) -> Identification:
        return Identification(
            id=IdentificationId(model.id),
            user_id=UserId(model.user_id),
            training_sample_id=TrainingIdentificationSampleId(model.training_sample_id),
            species_id=PlantSpeciesId(model.species_id),
            scientific_name=model.scientific_name,
            confidence=model.confidence,
            source=to_identification_origin(model.source),
            image_key=model.image_key,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: Identification) -> IdentificationModel:
        return IdentificationModel(
            id=entity.id,
            user_id=entity.user_id,
            training_sample_id=entity.training_sample_id,
            species_id=entity.species_id,
            scientific_name=entity.scientific_name,
            confidence=entity.confidence,
            source=entity.source,
            image_key=entity.image_key,
            created_at=entity.created_at,
        )
