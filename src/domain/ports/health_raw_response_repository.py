from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.value_objects.ids import HealthRecordId
from src.domain.value_objects.json_value import JsonObject


@dataclass(frozen=True)
class PendingHealthAssessment:
    """
    Avaliação do Kindwise guardada entre o diagnóstico e a confirmação do usuário: a resposta
    bruta (para o dataset de treino) e as imagens de referência que serão rehospedadas.
    """
    raw_response: JsonObject
    similar_images_urls: tuple[str, ...]


class IHealthRawResponseRepository(ABC):
    @abstractmethod
    async def save(self, health_record_id: HealthRecordId, assessment: PendingHealthAssessment) -> None:
        ...

    @abstractmethod
    async def get(self, health_record_id: HealthRecordId) -> PendingHealthAssessment | None:
        """None se a avaliação nunca existiu ou já expirou."""
        ...

    @abstractmethod
    async def delete(self, health_record_id: HealthRecordId) -> None:
        ...
