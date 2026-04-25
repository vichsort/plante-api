from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.health_identification_sample import HealthIdentificationSample

class IHealthIdentificationSampleRepository(ABC):
    @abstractmethod
    async def save(self, sample: HealthIdentificationSample) -> HealthIdentificationSample:
        ...

    @abstractmethod
    async def get_by_health_record_id(
        self,
        health_record_id: int,
    ) -> HealthIdentificationSample | None:
        """Busca a sample associada a um diagnóstico — usado no use case de confirmação."""
        ...

    @abstractmethod
    async def get_confirmed_before(
        self,
        cutoff: datetime,
    ) -> list[HealthIdentificationSample]:
        """Samples confirmadas antes do cutoff — usado pelo worker de anonimização."""
        ...

    @abstractmethod
    async def list_by_scientific_name(
        self,
        scientific_name: str,
        limit: int = 100,
    ) -> list[HealthIdentificationSample]:
        """Lista samples por espécie — usado no pipeline de treino da IA."""
        ...