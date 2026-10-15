from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.entities.training import FeedbackVerdict
from src.domain.use_cases.identify_plant_use_case import IdentifyPlantOutput


class IdentifyPlantResponse(BaseModel):
    identification_id: UUID
    scientific_name: str
    confidence: str
    image_url: str
    needs_human_review: bool

    @classmethod
    def from_domain(cls, output: IdentifyPlantOutput) -> "IdentifyPlantResponse":
        return cls(
            identification_id=output.identification_id,
            scientific_name=output.scientific_name,
            confidence=output.confidence.as_percentage(),
            image_url=output.image_url,
            needs_human_review=output.needs_human_review,
        )


class IdentificationFeedbackRequest(BaseModel):
    """Feedback sobre a identificação. `suggested_name`: a espécie que o usuário acha que é (opcional)."""
    verdict: FeedbackVerdict
    suggested_name: str | None = Field(default=None, min_length=1, max_length=255)
