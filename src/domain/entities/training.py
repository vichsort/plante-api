"""
Dados de treino da IA: anônimos por construção.

Nenhuma entidade daqui tem ID de usuário, referência a dado do usuário, foto do usuário (a
amostra tem a própria cópia, sem metadados), GPS exato ou horário exato (só o mês). Apagar
planta ou conta nunca apaga dado de treino. A confiança de cada rótulo não é calculada aqui:
guardam-se os sinais brutos (provedores + feedback) para a engine de confiança pesar depois.
"""
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import uuid4

from src.domain.entities.health_record import HealthSeverity
from src.domain.value_objects.ids import (
    TrainingFeedbackId,
    TrainingHealthSampleId,
    TrainingIdentificationSampleId,
)
from src.domain.value_objects.provider_signals import (
    HealthSignals,
    IdentificationSignals,
)
from src.domain.value_objects.sources import HealthSource, IdentificationOrigin
from src.domain.value_objects.training_location import TrainingLocation


def _check_period(period: date) -> None:
    if period.day != 1:
        raise ValueError("period must be the first day of a month (the exact date is not kept).")


@dataclass(frozen=True)
class TrainingIdentificationSample:
    id: TrainingIdentificationSampleId
    image_key: str
    scientific_name: str
    confidence: float
    source: IdentificationOrigin
    low_confidence: bool
    signals: tuple[IdentificationSignals, ...]
    period: date
    location: TrainingLocation
    family: str | None = None
    genus: str | None = None
    gbif_id: str | None = None
    provider_entity_id: str | None = None

    def __post_init__(self) -> None:
        if not self.scientific_name:
            raise ValueError("scientific_name cannot be empty.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0.")
        _check_period(self.period)

    @staticmethod
    def new_id() -> TrainingIdentificationSampleId:
        return TrainingIdentificationSampleId(uuid4())


@dataclass(frozen=True)
class TrainingHealthSample:
    id: TrainingHealthSampleId
    image_key: str
    scientific_name: str
    vitality_score: float
    severity: HealthSeverity
    source: HealthSource
    signals: HealthSignals
    period: date
    location: TrainingLocation
    issues_detected: tuple[str, ...] = ()
    treatment_plan: tuple[str, ...] = ()
    reference_image_keys: tuple[str, ...] = ()
    recovery_estimate_days: int | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.vitality_score <= 1.0:
            raise ValueError("vitality_score must be between 0.0 and 1.0.")
        _check_period(self.period)

    @staticmethod
    def new_id() -> TrainingHealthSampleId:
        return TrainingHealthSampleId(uuid4())


class FeedbackVerdict(StrEnum):
    CORRECT = "correct"
    WRONG = "wrong"
    UNSURE = "unsure"


class FeedbackOrigin(StrEnum):
    EXPLICIT = "explicit"                # o usuário respondeu "acertou / errou / não sei"
    ADDED_TO_GARDEN = "added_to_garden"  # sinal implícito: adicionou a planta ao jardim


@dataclass(frozen=True)
class TrainingFeedback:
    """
    Um sinal sobre um rótulo. Eventos acumulam (o usuário pode mudar de ideia); quem decide como
    pesar a sequência é a engine de confiança. Aponta para exatamente uma amostra.
    """
    id: TrainingFeedbackId
    verdict: FeedbackVerdict
    origin: FeedbackOrigin
    given_on: date
    identification_sample_id: TrainingIdentificationSampleId | None = None
    health_sample_id: TrainingHealthSampleId | None = None
    suggested_name: str | None = None

    def __post_init__(self) -> None:
        if (self.identification_sample_id is None) == (self.health_sample_id is None):
            raise ValueError("Feedback must target exactly one training sample.")
        if self.suggested_name is not None and not self.suggested_name.strip():
            raise ValueError("suggested_name cannot be blank.")

    @classmethod
    def on_identification(
        cls,
        sample_id: TrainingIdentificationSampleId,
        verdict: FeedbackVerdict,
        origin: FeedbackOrigin,
        given_on: date,
        suggested_name: str | None = None,
    ) -> "TrainingFeedback":
        return cls(
            id=TrainingFeedbackId(uuid4()),
            verdict=verdict,
            origin=origin,
            given_on=given_on,
            identification_sample_id=sample_id,
            suggested_name=suggested_name.strip() if suggested_name else None,
        )

    @classmethod
    def on_health(
        cls,
        sample_id: TrainingHealthSampleId,
        verdict: FeedbackVerdict,
        given_on: date,
    ) -> "TrainingFeedback":
        return cls(
            id=TrainingFeedbackId(uuid4()),
            verdict=verdict,
            origin=FeedbackOrigin.EXPLICIT,
            given_on=given_on,
            health_sample_id=sample_id,
        )
