from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.entities.health_record import HealthRecord, HealthSeverity
from src.domain.entities.training import FeedbackVerdict
from src.domain.use_cases.diagnose_health_use_case import DiagnoseHealthOutput


class HealthFeedbackRequest(BaseModel):
    """Feedback do usuário sobre o diagnóstico: acertou, errou ou não sabe."""
    verdict: FeedbackVerdict

class HealthDiagnosisResponse(BaseModel):
    health_record_id: UUID
    severity: HealthSeverity
    vitality_score: float
    is_healthy: bool
    issues_detected: list[str]
    treatment_plan: list[str]
    recovery_estimate_days: int | None = None
    image_key: str
    similar_images_urls: list[str]

    @classmethod
    def from_domain(cls, output: DiagnoseHealthOutput) -> "HealthDiagnosisResponse":
        record = output.record
        return cls(
            health_record_id=record.id,
            severity=record.severity,
            vitality_score=record.vitality_score,
            is_healthy=record.is_healthy,
            issues_detected=list(record.issues_detected),
            treatment_plan=list(record.treatment_plan),
            recovery_estimate_days=record.recovery_estimate_days,
            image_key=record.image_key,
            similar_images_urls=list(output.similar_images_urls),
        )

class HealthRecordItemResponse(BaseModel):
    health_record_id: UUID
    diagnosed_at: datetime | None
    severity: HealthSeverity
    vitality_score: float
    is_healthy: bool
    issues_detected: list[str]
    treatment_plan: list[str]
    recovery_estimate_days: int | None = None
    image_key: str

    @classmethod
    def from_domain(cls, record: HealthRecord) -> "HealthRecordItemResponse":
        return cls(
            health_record_id=record.id,
            diagnosed_at=record.diagnosed_at,
            severity=record.severity,
            vitality_score=record.vitality_score,
            is_healthy=record.is_healthy,
            issues_detected=list(record.issues_detected),
            treatment_plan=list(record.treatment_plan),
            recovery_estimate_days=record.recovery_estimate_days,
            image_key=record.image_key,
        )
