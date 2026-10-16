from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from src.domain.value_objects.ids import (
    HealthRecordId,
    TrainingHealthSampleId,
    UserPlantId,
)
from src.domain.value_objects.sources import HealthSource
from src.shared.domain import UserId


class HealthSeverity(StrEnum):
    HEALTHY = "healthy"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass(frozen=True)
class HealthRecord:
    id: HealthRecordId
    user_plant_id: UserPlantId
    scientific_name: str
    vitality_score: float
    severity: HealthSeverity
    source: HealthSource
    image_key: str
    # Vínculo de mão única com a amostra de treino anônima (que não aponta de volta)
    training_sample_id: TrainingHealthSampleId
    diagnosed_at: datetime | None = None
    user_id: UserId | None = None
    issues_detected: tuple[str, ...] = field(default_factory=tuple)
    treatment_plan: tuple[str, ...] = field(default_factory=tuple)
    recovery_estimate_days: int | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.vitality_score <= 1.0:
            raise ValueError("vitality_score needs to be between 0.0 and 1.0.")

    @property
    def is_healthy(self) -> bool:
        return self.severity == HealthSeverity.HEALTHY

    @property
    def needs_attention(self) -> bool:
        return self.severity in (
            HealthSeverity.MODERATE,
            HealthSeverity.HIGH,
            HealthSeverity.CRITICAL,
        )