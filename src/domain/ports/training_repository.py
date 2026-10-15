from abc import ABC, abstractmethod

from src.domain.entities.training import (
    TrainingFeedback,
    TrainingHealthSample,
    TrainingIdentificationSample,
)
from src.domain.value_objects.ids import (
    TrainingHealthSampleId,
    TrainingIdentificationSampleId,
)


class ITrainingRepository(ABC):
    """
    Dados de treino: só se acrescenta. Não há remoção — nenhuma ação do usuário apaga dado de
    treino (ele não tem como ser associado a ninguém).
    """

    @abstractmethod
    async def add_identification_sample(self, sample: TrainingIdentificationSample) -> None:
        ...

    @abstractmethod
    async def add_health_sample(self, sample: TrainingHealthSample) -> None:
        ...

    @abstractmethod
    async def add_feedback(self, feedback: TrainingFeedback) -> None:
        ...

    @abstractmethod
    async def get_identification_sample(
        self, sample_id: TrainingIdentificationSampleId
    ) -> TrainingIdentificationSample | None:
        ...

    @abstractmethod
    async def get_health_sample(self, sample_id: TrainingHealthSampleId) -> TrainingHealthSample | None:
        ...

    @abstractmethod
    async def list_feedback(
        self, sample_id: TrainingIdentificationSampleId | TrainingHealthSampleId
    ) -> list[TrainingFeedback]:
        """Eventos de feedback de uma amostra, do mais antigo ao mais recente."""
        ...
