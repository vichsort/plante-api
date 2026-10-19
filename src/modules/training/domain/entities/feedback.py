"""
Feedback: um sinal sobre um rótulo do dataset. Eventos acumulam (o usuário pode mudar de ideia); a
engine de confiança decide como pesar a sequência. Anônimo como as amostras: não diz de quem veio.
"""
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import uuid4

from src.modules.training.domain.value_objects.ids import (
    TrainingFeedbackId,
    TrainingHealthSampleId,
    TrainingIdentificationSampleId,
)


class FeedbackVerdict(StrEnum):
    CORRECT = "correct"
    WRONG = "wrong"
    UNSURE = "unsure"


class FeedbackOrigin(StrEnum):
    EXPLICIT = "explicit"                # o usuário respondeu "acertou / errou / não sei"
    ADDED_TO_GARDEN = "added_to_garden"  # sinal implícito: adicionou a planta ao jardim
    # Implicit, from taking the plant out of the garden. Only `removed_misidentified` votes (WRONG);
    # the others come with UNSURE, meaning "an event with no vote on the label"
    REMOVED_MISIDENTIFIED = "removed_misidentified"
    REMOVED_DIED = "removed_died"
    REMOVED_GAVE_AWAY = "removed_gave_away"
    REMOVED_OTHER = "removed_other"


@dataclass(frozen=True)
class IdentificationLabel:
    """Voto sobre "esta espécie está certa?". A sugestão é só uma candidata, sem peso próprio."""
    sample_id: TrainingIdentificationSampleId
    suggested_name: str | None = None

    def __post_init__(self) -> None:
        if self.suggested_name is not None and not self.suggested_name.strip():
            raise ValueError("suggested_name cannot be blank.")


@dataclass(frozen=True)
class HealthLabel:
    """Voto sobre "este diagnóstico está certo?"."""
    sample_id: TrainingHealthSampleId


# Em que se vota e para quê. Alvo novo (ex.: um problema do diagnóstico) = mais um tipo aqui, e o
# mypy aponta todo `match` que ficar incompleto
FeedbackTarget = IdentificationLabel | HealthLabel


@dataclass(frozen=True)
class TrainingFeedback:
    id: TrainingFeedbackId
    target: FeedbackTarget
    verdict: FeedbackVerdict
    origin: FeedbackOrigin
    given_on: date

    @classmethod
    def create(
        cls, target: FeedbackTarget, verdict: FeedbackVerdict, origin: FeedbackOrigin, given_on: date,
    ) -> "TrainingFeedback":
        if isinstance(target, IdentificationLabel) and target.suggested_name is not None:
            target = IdentificationLabel(target.sample_id, target.suggested_name.strip())
        return cls(id=TrainingFeedbackId(uuid4()), target=target, verdict=verdict, origin=origin, given_on=given_on)
