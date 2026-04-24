from src.domain.entities.plant_reference_image import PlantReferenceImage, ImageSource
from src.adapters.persistence.models import PlantReferenceImageModel

class PlantReferenceImageMapper:
    @staticmethod
    def to_domain(model: PlantReferenceImageModel) -> PlantReferenceImage:
        return PlantReferenceImage(
            id=model.id,
            scientific_name=model.scientific_name,
            storage_key=model.storage_key,
            source=ImageSource(model.source),
            created_at=model.created_at,
            user_id=model.user_id,
        )

    @staticmethod
    def to_model(entity: PlantReferenceImage) -> PlantReferenceImageModel:
        return PlantReferenceImageModel(
            id=entity.id,
            scientific_name=entity.scientific_name,
            storage_key=entity.storage_key,
            source=entity.source.value,
            created_at=entity.created_at,
            user_id=entity.user_id,
        )