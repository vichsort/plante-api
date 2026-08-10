from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class HealthSeverity(Enum):
    HEALTHY = "healthy"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass(frozen=True)
class HealthRecord:
    id: Any
    user_plant_id: Any
    scientific_name: str
    vitality_score: float
    severity: HealthSeverity
    source: str
    image_key: str
    diagnosed_at: datetime | None = None
    user_id: Any = None
    issues_detected: tuple[str, ...] = field(default_factory=tuple)
    treatment_plan: tuple[str, ...] = field(default_factory=tuple)
    recovery_estimate_days: int | None = None
    notes: str | None = None

    def __post_init__(self):
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