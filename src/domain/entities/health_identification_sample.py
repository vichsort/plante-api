from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class HealthSampleStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"

@dataclass(frozen=True)
class HealthIdentificationSample:
    """
    Registro imutável de um diagnóstico de saúde confirmado pelo usuário.
    Destinado ao dataset de treino da IA — não contém dados pessoais após anonimização.
    """

    id: Any
    health_record_id: Any
    scientific_name: str
    user_image_key: str
    vitality_score: float
    issues_detected: tuple[str, ...]
    treatment_plan: tuple[str, ...]
    identification_source: str
    raw_response: dict[str, Any]
    status: HealthSampleStatus
    created_at: datetime

    reference_image_keys: tuple[str, ...] = ()
    user_id: Any = None
    confirmed_at: datetime | None = None
    rejected_at: datetime | None = None
    recovery_estimate_days: int | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.scientific_name:
            raise ValueError("scientific_name cannot be empty.")
        if not self.user_image_key:
            raise ValueError("user_image_key cannot be empty.")
        if not 0.0 <= self.vitality_score <= 1.0:
            raise ValueError("vitality_score must be between 0.0 and 1.0.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")
        if self.status == HealthSampleStatus.CONFIRMED and self.confirmed_at is None:
            raise ValueError("confirmed samples must have confirmed_at.")
        if self.status == HealthSampleStatus.REJECTED and self.rejected_at is None:
            raise ValueError("rejected samples must have rejected_at.")

    def confirm(self, confirmed_at: datetime) -> "HealthIdentificationSample":
        if self.status != HealthSampleStatus.PENDING:
            raise ValueError("Only pending samples can be confirmed.")
        import dataclasses
        return dataclasses.replace(self, status=HealthSampleStatus.CONFIRMED, confirmed_at=confirmed_at)

    def reject(self, rejected_at: datetime) -> "HealthIdentificationSample":
        if self.status != HealthSampleStatus.PENDING:
            raise ValueError("Only pending samples can be rejected.")
        import dataclasses
        return dataclasses.replace(self, status=HealthSampleStatus.REJECTED, rejected_at=rejected_at)

    def anonymize(self) -> "HealthIdentificationSample":
        import dataclasses
        return dataclasses.replace(self, user_id=None)