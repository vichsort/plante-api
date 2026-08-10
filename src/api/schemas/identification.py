from pydantic import BaseModel


class IdentifyPlantRequest(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    country: str | None = None
    state: str | None = None

class IdentifyPlantResponse(BaseModel):
    user_plant_id: str
    sample_id: str
    scientific_name: str
    confidence: str
    image_url: str
    needs_human_review: bool

class ConfirmPlantIdentificationRequest(BaseModel):
    sample_id: str

class ConfirmPlantIdentificationResponse(BaseModel):
    sample_id: str
    scientific_name: str
    status: str
    confirmed_at: str