from abc import ABC, abstractmethod

from src.domain.entities.health_record import HealthRecord
from src.domain.value_objects.ids import HealthRecordId
from src.modules.garden import UserPlantId
from src.shared.domain import UserId


class IHealthRecordRepository(ABC):
    @abstractmethod
    async def save(self, record: HealthRecord) -> HealthRecord:
        ...

    @abstractmethod
    async def get_for_user(self, record_id: HealthRecordId, user_id: UserId) -> HealthRecord | None:
        """O diagnóstico, se for deste usuário (de outro, ou inexistente: None)."""
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