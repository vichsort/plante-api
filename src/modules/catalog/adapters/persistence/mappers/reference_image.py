from src.modules.catalog.adapters.persistence.models.reference_image import (
    PlantReferenceImageModel,
)
from src.modules.catalog.domain.entities.reference_image import PlantReferenceImage
from src.modules.catalog.domain.value_objects.ids import ReferenceImageId
from src.shared.domain import UserId


class PlantReferenceImageMapper:
    @staticmethod
    def to_domain(model: PlantReferenceImageModel) -> PlantReferenceImage:
        return PlantReferenceImage(
            id=ReferenceImageId(model.id),
            scientific_name=model.scientific_name,
            storage_key=model.storage_key,
            source=model.source,
            created_at=model.created_at,
            user_id=UserId(model.user_id) if model.user_id else None,
        )

    @staticmethod
    def to_model(entity: PlantReferenceImage) -> PlantReferenceImageModel:
        return PlantReferenceImageModel(
            id=entity.id,
            scientific_name=entity.scientific_name,
            storage_key=entity.storage_key,
            source=entity.source,
            created_at=entity.created_at,
            user_id=entity.user_id,
        )