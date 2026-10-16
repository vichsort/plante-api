from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from src.domain.entities.care_schedule import CareType
from src.domain.entities.user_plant import IdentificationSource, IdentificationStatus
from src.domain.use_cases.get_plant_details_use_case import PlantDetailsOutput
from src.modules.catalog import LightRequirement, PlantSpecies, SoilType


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
