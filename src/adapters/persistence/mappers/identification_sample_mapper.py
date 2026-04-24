from src.domain.entities.plant_identification_sample import PlantIdentificationSample, SampleStatus
from src.adapters.persistence.models import PlantIdentificationSampleModel

class IdentificationSampleMapper:
    @staticmethod
    def to_domain(model: PlantIdentificationSampleModel) -> PlantIdentificationSample:
        return PlantIdentificationSample(
            id=model.id,
            scientific_name=model.scientific_name,
            species_id=model.species_id,
            user_image_key=model.user_image_key,
            identification_confidence=model.identification_confidence,
            identification_source=model.identification_source,
            raw_response=model.raw_response,
            status=SampleStatus(model.status),
            created_at=model.created_at,
            user_id=model.user_id,
            confirmed_at=model.confirmed_at,
            rejected_at=model.rejected_at,
            has_deep_analysis=model.has_deep_analysis,
            has_nutritional_analysis=model.has_nutritional_analysis,
        )

    @staticmethod
    def to_model(entity: PlantIdentificationSample) -> PlantIdentificationSampleModel:
        return PlantIdentificationSampleModel(
            id=entity.id,
            scientific_name=entity.scientific_name,
            species_id=entity.species_id,
            user_image_key=entity.user_image_key,
            identification_confidence=entity.identification_confidence,
            identification_source=entity.identification_source,
            raw_response=entity.raw_response,
            status=entity.status.value,
            created_at=entity.created_at,
            user_id=entity.user_id,
            confirmed_at=entity.confirmed_at,
            rejected_at=entity.rejected_at,
            has_deep_analysis=entity.has_deep_analysis,
            has_nutritional_analysis=entity.has_nutritional_analysis,
        )