from abc import ABC, abstractmethod
from src.domain.entities.plant_species import PlantSpecies, EnrichmentStatus

class IPlantSpeciesRepository(ABC):
    @abstractmethod
    async def save(self, species: PlantSpecies) -> PlantSpecies:
        ...

    @abstractmethod
    async def get_by_scientific_name(self, scientific_name: str) -> PlantSpecies | None:
        ...

    @abstractmethod
    async def update_enrichment_status(
        self,
        scientific_name: str,
        status: EnrichmentStatus,
    ) -> None:
        ...

    @abstractmethod
    async def list_pending_enrichment(self, limit: int = 50) -> list[PlantSpecies]:
        """Usado pelo Celery pra buscar espécies que ainda precisam de enriquecimento."""
        ...