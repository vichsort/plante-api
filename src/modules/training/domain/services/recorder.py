from abc import ABC, abstractmethod
from datetime import date

from src.modules.training.domain.entities.feedback import (
    FeedbackOrigin,
    FeedbackTarget,
    FeedbackVerdict,
    TrainingFeedback,
)
from src.modules.training.domain.entities.samples import (
    TrainingHealthSample,
    TrainingIdentificationSample,
)
from src.modules.training.domain.ports.unit_of_work import ITrainingUnitOfWork


class ITrainingRecorder(ABC):
    """
    Única porta de escrita no dataset, para os outros módulos. Só acrescenta (nada é apagado por
    ação do usuário) e roda **dentro da transação de quem chama**: a amostra de treino é gravada
    junto com a identificação ou o diagnóstico, ou nada é.
    """

    @abstractmethod
    async def record_identification_sample(self, sample: TrainingIdentificationSample) -> None:
        ...

    @abstractmethod
    async def record_health_sample(self, sample: TrainingHealthSample) -> None:
        ...

    @abstractmethod
    async def record_feedback(
        self, target: FeedbackTarget, verdict: FeedbackVerdict, origin: FeedbackOrigin, given_on: date,
    ) -> None:
        ...


class TrainingRecorder(ITrainingRecorder):
    def __init__(self, uow: ITrainingUnitOfWork) -> None:
        self.uow = uow

    async def record_identification_sample(self, sample: TrainingIdentificationSample) -> None:
        async with self.uow as uow:
            _require_callers_transaction(uow)
            await uow.training.add_identification_sample(sample)

    async def record_health_sample(self, sample: TrainingHealthSample) -> None:
        async with self.uow as uow:
            _require_callers_transaction(uow)
            await uow.training.add_health_sample(sample)

    async def record_feedback(
        self, target: FeedbackTarget, verdict: FeedbackVerdict, origin: FeedbackOrigin, given_on: date,
    ) -> None:
        async with self.uow as uow:
            _require_callers_transaction(uow)
            await uow.training.add_feedback(TrainingFeedback.create(target, verdict, origin, given_on))


def _require_callers_transaction(uow: ITrainingUnitOfWork) -> None:
    # Fora de uma transação aberta por quem chama, a gravação nunca seria confirmada (service não
    # faz commit): falhar alto em vez de perder a amostra em silêncio
    if not uow.joined:
        raise RuntimeError("TrainingRecorder must be called inside the caller's unit of work.")
