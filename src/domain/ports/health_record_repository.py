from abc import ABC, abstractmethod
from src.domain.entities.health_record import HealthRecord

class IHealthRecordRepository(ABC):
    @abstractmethod
    async def save(self, record: HealthRecord) -> HealthRecord:
        ...

    @abstractmethod
    async def get_by_id(self, record_id: int) -> HealthRecord | None:
        """Busca um diagnóstico pelo id — usado no use case de confirmação."""
        ...

    @abstractmethod
    async def get_latest_by_plant(self, user_plant_id: int) -> HealthRecord | None:
        """Diagnóstico mais recente — usado na tela principal da planta."""
        ...

    @abstractmethod
    async def list_by_plant(
        self,
        user_plant_id: int,
        limit: int = 20,
    ) -> list[HealthRecord]:
        """Histórico completo — usado na tela de evolução da planta."""
        ...