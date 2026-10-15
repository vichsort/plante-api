from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.entities.plant_identification_sample import (
    PlantIdentificationSample,
    SampleStatus,
)
from src.domain.use_cases.identify_plant_use_case import IdentifyPlantOutput


class IdentifyPlantResponse(BaseModel):
    user_plant_id: UUID
    sample_id: UUID
    scientific_name: str
    confidence: str
    image_url: str
    needs_human_review: bool

    @classmethod
    def from_domain(cls, output: IdentifyPlantOutput) -> "IdentifyPlantResponse":
        return cls(
            user_plant_id=output.user_plant_id,
            sample_id=output.sample_id,
            scientific_name=output.scientific_name,
            confidence=output.confidence.as_percentage(),
            image_url=output.image_url,
            needs_human_review=output.needs_human_review,
        )

class ConfirmPlantIdentificationRequest(BaseModel):
    sample_id: UUID

class ConfirmPlantIdentificationResponse(BaseModel):
    sample_id: UUID
    scientific_name: str
    status: SampleStatus
    confirmed_at: datetime | None

    @classmethod
    def from_domain(cls, sample: PlantIdentificationSample) -> "ConfirmPlantIdentificationResponse":
        return cls(
            sample_id=sample.id,
            scientific_name=sample.scientific_name,
            status=sample.status,
            confirmed_at=sample.confirmed_at,
        )
