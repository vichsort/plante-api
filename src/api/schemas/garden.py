from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.entities.user_plant import GardenPlant, UserPlant


class AddPlantToGardenRequest(BaseModel):
    """Adiciona ao jardim a planta de uma identificação (`POST /identify` devolve o ID)."""
    identification_id: UUID
    nickname: str | None = Field(default=None, min_length=1, max_length=100)


class WaterPlantResponse(BaseModel):
    user_plant_id: UUID
    last_watered_at: datetime | None = None
    next_due_on: date | None = None
    current_streak: int

    @classmethod
    def from_domain(cls, plant: UserPlant) -> "WaterPlantResponse":
        return cls(
            user_plant_id=plant.id,
            last_watered_at=plant.last_watered_at,
            next_due_on=plant.care_schedule.next_due_on,
            current_streak=plant.watering_streak.current_count,
        )

class GardenItemResponse(BaseModel):
    id: UUID
    scientific_name: str
    nickname: str | None = None
    display_name: str
    primary_image_url: str | None = None
    last_watered_at: datetime | None = None
    next_due_on: date | None = None
    needs_watering: bool
    streak_count: int

    @classmethod
    def from_domain(cls, item: GardenPlant) -> "GardenItemResponse":
        plant = item.plant
        return cls(
            id=plant.id,
            scientific_name=plant.scientific_name,
            nickname=plant.nickname,
            display_name=plant.display_name,
            primary_image_url=plant.primary_image_url,
            last_watered_at=plant.last_watered_at,
            next_due_on=plant.care_schedule.next_due_on,
            needs_watering=item.needs_watering,
            streak_count=plant.watering_streak.current_count,
        )
