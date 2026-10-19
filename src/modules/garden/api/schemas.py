from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.catalog import LightRequirement, PlantSpecies, SoilType
from src.modules.garden.domain.entities.care_schedule import CareType
from src.modules.garden.domain.entities.user_plant import (
    GardenPlant,
    IdentificationSource,
    IdentificationStatus,
    UserPlant,
)
from src.modules.garden.domain.use_cases.get_plant_details import PlantDetailsOutput


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


class CareScheduleResponse(BaseModel):
    care_type: CareType
    interval_days: int
    is_active: bool
    next_due_on: date | None

class SpeciesInfoResponse(BaseModel):
    family: str | None
    genus: str | None
    common_names: list[str]
    is_edible: bool | None
    water_frequency_per_week: int | None
    light_requirement: LightRequirement | None
    soil_type: SoilType | None
    habitat: str | None

    @classmethod
    def from_domain(cls, species: PlantSpecies) -> "SpeciesInfoResponse":
        return cls(
            family=species.family,
            genus=species.genus,
            common_names=list(species.common_names),
            is_edible=species.is_edible,
            water_frequency_per_week=species.water_frequency_per_week,
            light_requirement=species.light_requirement,
            soil_type=species.soil_type,
            habitat=species.habitat,
        )

class PlantDetailsResponse(BaseModel):
    id: UUID
    user_id: UUID
    scientific_name: str
    nickname: str | None
    display_name: str
    primary_image_url: str | None
    identification_confidence: float
    identification_source: IdentificationSource
    status: IdentificationStatus
    added_at: datetime | None
    last_watered_at: datetime | None
    needs_watering: bool
    watering_streak: int
    care_schedule: CareScheduleResponse
    species_info: SpeciesInfoResponse | None

    @classmethod
    def from_domain(cls, details: PlantDetailsOutput) -> "PlantDetailsResponse":
        plant = details.plant
        care = plant.care_schedule
        return cls(
            id=plant.id,
            user_id=plant.user_id,
            scientific_name=plant.scientific_name,
            nickname=plant.nickname,
            display_name=plant.display_name,
            primary_image_url=plant.primary_image_url,
            identification_confidence=plant.identification_confidence,
            identification_source=plant.identification_source,
            status=plant.status,
            added_at=plant.added_at,
            last_watered_at=plant.last_watered_at,
            needs_watering=details.needs_watering,
            watering_streak=plant.watering_streak.current_count,
            care_schedule=CareScheduleResponse(
                care_type=care.care_type,
                interval_days=care.interval.days,
                is_active=care.is_active,
                next_due_on=care.next_due_on,
            ),
            species_info=SpeciesInfoResponse.from_domain(details.species) if details.species else None,
        )
