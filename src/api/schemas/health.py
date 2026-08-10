from pydantic import BaseModel


class ConfirmHealthDiagnosisRequest(BaseModel):
    health_record_id: str

class HealthDiagnosisResponse(BaseModel):
    health_record_id: str
    severity: str
    vitality_score: float
    is_healthy: bool
    issues_detected: list[str]
    treatment_plan: list[str]
    recovery_estimate_days: int | None = None
    image_key: str
    similar_images_urls: list[str]

class ConfirmHealthDiagnosisResponse(BaseModel):
    sample_id: str
    health_record_id: str
    scientific_name: str
    status: str
    confirmed_at: str

class HealthRecordItemResponse(BaseModel):
    health_record_id: str
    diagnosed_at: str
    severity: str
    vitality_score: float
    is_healthy: bool
    issues_detected: list[str]
    treatment_plan: list[str]
    recovery_estimate_days: int | None = None
    image_key: str | None = None
