from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.entities.health_identification_sample import (
    HealthIdentificationSample,
    HealthSampleStatus,
)
from src.domain.entities.health_record import HealthRecord, HealthSeverity
from src.domain.use_cases.diagnose_health_use_case import DiagnoseHealthOutput


class ConfirmHealthDiagnosisRequest(BaseModel):
    health_record_id: UUID

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

class ConfirmHealthDiagnosisResponse(BaseModel):
    sample_id: UUID
    health_record_id: UUID
    scientific_name: str
    status: HealthSampleStatus
    confirmed_at: datetime | None

    @classmethod
    def from_domain(cls, sample: HealthIdentificationSample) -> "ConfirmHealthDiagnosisResponse":
        return cls(
            sample_id=sample.id,
            health_record_id=sample.health_record_id,
            scientific_name=sample.scientific_name,
            status=sample.status,
            confirmed_at=sample.confirmed_at,
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
