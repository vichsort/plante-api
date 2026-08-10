from pydantic import BaseModel


class AddPlantToGardenRequest(BaseModel):
    user_plant_id: str
    sample_id: str

class DeleteUserPlantRequest(BaseModel):
    sample_id: str

class WaterPlantResponse(BaseModel):
    user_plant_id: str
    last_watered_at: str | None = None
    next_due_at: str | None = None
    current_streak: int

class GardenItemResponse(BaseModel):
    id: str
    scientific_name: str
    nickname: str | None = None
    display_name: str
    primary_image_url: str | None = None
    last_watered_at: str | None = None
    next_due_at: str | None = None
    needs_watering: bool
    streak_count: int
