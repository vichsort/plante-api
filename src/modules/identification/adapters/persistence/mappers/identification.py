from src.modules.catalog import PlantSpeciesId
from src.modules.identification.adapters.persistence.models.identification import (
    IdentificationModel,
)
from src.modules.identification.domain.entities.identification import Identification
from src.modules.identification.domain.value_objects.ids import IdentificationId
from src.modules.training import (
    TrainingIdentificationSampleId,
    parse_identification_origin,
)
from src.shared.domain import UserId


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
            source=parse_identification_origin(model.source),
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
