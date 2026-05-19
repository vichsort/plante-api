from pydantic import BaseModel, Field, field_validator
import base64

class IdentifyPlantRequest(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    country: str | None = None
    state: str | None = None

class IdentifyPlantResponse(BaseModel):
    user_plant_id: int
    sample_id: int
    scientific_name: str
    confidence: str
    image_url: str
    needs_human_review: bool