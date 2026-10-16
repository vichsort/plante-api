from abc import ABC, abstractmethod

from src.modules.catalog.domain.entities.nutritional import PlantNutritional


class IPlantNutritionalRepository(ABC):

    @abstractmethod
    async def save(self, nutritional: PlantNutritional) -> PlantNutritional:
        ...

    @abstractmethod
    async def get_by_scientific_name(self, scientific_name: str) -> PlantNutritional | None:
        ...