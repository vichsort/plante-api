from abc import ABC, abstractmethod

from src.domain.entities.health_record import HealthRecord
from src.domain.value_objects.ids import HealthRecordId, UserPlantId


class IHealthRecordRepository(ABC):
    @abstractmethod
    async def save(self, record: HealthRecord) -> HealthRecord:
        ...

    @abstractmethod
    async def get_by_id(self, record_id: HealthRecordId) -> HealthRecord | None:
        """Busca um diagnóstico pelo id — usado no use case de confirmação."""
        ...

    @abstractmethod
    async def get_latest_by_plant(self, user_plant_id: UserPlantId) -> HealthRecord | None:
        """Diagnóstico mais recente — usado na tela principal da planta."""
        ...

    @abstractmethod
    async def list_by_plant(
        self,
        user_plant_id: UserPlantId,
        limit: int = 20,
    ) -> list[HealthRecord]:
        """Histórico completo — usado na tela de evolução da planta."""
        ...