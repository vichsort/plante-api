"""Dublê do `ITrainingRecorder` para os testes de quem grava no dataset (outros módulos e o código antigo)."""
from dataclasses import dataclass, field
from datetime import date

from src.modules.training.domain.entities.feedback import (
    FeedbackOrigin,
    FeedbackTarget,
    FeedbackVerdict,
)
from src.modules.training.domain.entities.samples import (
    TrainingHealthSample,
    TrainingIdentificationSample,
)
from src.modules.training.domain.services.recorder import ITrainingRecorder


@dataclass(frozen=True)
class RecordedFeedback:
    target: FeedbackTarget
    verdict: FeedbackVerdict
    origin: FeedbackOrigin
    given_on: date


@dataclass
class FakeTrainingRecorder(ITrainingRecorder):
    """Guarda o que seria gravado, na ordem."""
    identification_samples: list[TrainingIdentificationSample] = field(default_factory=list)
    health_samples: list[TrainingHealthSample] = field(default_factory=list)
    feedback: list[RecordedFeedback] = field(default_factory=list)

    async def record_identification_sample(self, sample: TrainingIdentificationSample) -> None:
        self.identification_samples.append(sample)

    async def record_health_sample(self, sample: TrainingHealthSample) -> None:
        self.health_samples.append(sample)

    async def record_feedback(
        self, target: FeedbackTarget, verdict: FeedbackVerdict, origin: FeedbackOrigin, given_on: date,
    ) -> None:
        self.feedback.append(RecordedFeedback(target, verdict, origin, given_on))

    @property
    def is_empty(self) -> bool:
        return not (self.identification_samples or self.health_samples or self.feedback)
