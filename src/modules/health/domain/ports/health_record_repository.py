from abc import ABC, abstractmethod

from src.modules.garden import UserPlantId
from src.modules.health.domain.entities.health_record import HealthRecord
from src.modules.health.domain.value_objects.ids import HealthRecordId
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
    async def list_by_plant(
        self,
        user_plant_id: UserPlantId,
        limit: int = 20,
    ) -> list[HealthRecord]:
        """Os diagnósticos da planta, do mais recente ao mais antigo (tela de evolução da planta)."""
        ...