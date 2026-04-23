from abc import ABC, abstractmethod
from src.domain.entities.plant_reference_image import PlantReferenceImage

class IPlantReferenceImageRepository(ABC):

    @abstractmethod
    async def save(self, image: PlantReferenceImage) -> PlantReferenceImage:
        ...

    @abstractmethod
    async def get_by_scientific_name(self, scientific_name: str) -> list[PlantReferenceImage]:
        ...