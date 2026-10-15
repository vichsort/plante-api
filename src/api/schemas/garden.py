from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.entities.user_plant import UserPlant


class AddPlantToGardenRequest(BaseModel):
    user_plant_id: UUID
    sample_id: UUID

class DeleteUserPlantRequest(BaseModel):
    sample_id: UUID

class WaterPlantResponse(BaseModel):
    user_plant_id: UUID
    last_watered_at: datetime | None = None
    next_due_at: datetime | None = None
    current_streak: int

    @classmethod
    def from_domain(cls, plant: UserPlant) -> "WaterPlantResponse":
        return cls(
            user_plant_id=plant.id,
            last_watered_at=plant.last_watered_at,
            next_due_at=plant.care_schedule.next_due_at,
            current_streak=plant.watering_streak.current_count,
        )

class GardenItemResponse(BaseModel):
    id: UUID
    scientific_name: str
    nickname: str | None = None
    display_name: str
    primary_image_url: str | None = None
    last_watered_at: datetime | None = None
    next_due_at: datetime | None = None
    needs_watering: bool
    streak_count: int

    @classmethod
    def from_domain(cls, plant: UserPlant) -> "GardenItemResponse":
        return cls(
            id=plant.id,
            scientific_name=plant.scientific_name,
            nickname=plant.nickname,
            display_name=plant.display_name,
            primary_image_url=plant.primary_image_url,
            last_watered_at=plant.last_watered_at,
            next_due_at=plant.care_schedule.next_due_at,
            needs_watering=plant.needs_watering,
            streak_count=plant.watering_streak.current_count,
        )
