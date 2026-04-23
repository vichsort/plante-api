from abc import ABC, abstractmethod
from src.domain.entities.plant_identification_sample import PlantIdentificationSample

class IIdentificationSampleRepository(ABC):

    @abstractmethod
    async def save(self, sample: PlantIdentificationSample) -> PlantIdentificationSample:
        ...

    @abstractmethod
    async def get_by_id(self, sample_id: int) -> PlantIdentificationSample | None:
        ...

    @abstractmethod
    async def get_pending_by_user(self, user_id: int) -> list[PlantIdentificationSample]:
        """Busca identificações aguardando confirmação do usuário."""
        ...

    @abstractmethod
    async def get_complete_for_training(self, limit: int = 100) -> list[PlantIdentificationSample]:
        """Busca samples completas para exportação ao pipeline de ML."""
        ...