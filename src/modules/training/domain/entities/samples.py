"""
Dados de treino da IA: anônimos por construção.

Nenhuma entidade daqui tem ID de usuário, referência a dado do usuário, foto do usuário (a
amostra tem a própria cópia, sem metadados), GPS exato ou horário exato (só o mês). Apagar
planta ou conta nunca apaga dado de treino. A confiança de cada rótulo não é calculada aqui:
guardam-se os sinais brutos (provedores + feedback) para a engine de confiança pesar depois.
"""
from dataclasses import dataclass
from datetime import date
from uuid import uuid4

from src.modules.training.domain.value_objects.ids import (
    TrainingHealthSampleId,
    TrainingIdentificationSampleId,
)
from src.modules.training.domain.value_objects.location import TrainingLocation
from src.modules.training.domain.value_objects.provenance import (
    HealthSeverity,
    HealthSource,
    IdentificationOrigin,
)
from src.modules.training.domain.value_objects.provider_signals import (
    HealthSignals,
    IdentificationSignals,
)


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
