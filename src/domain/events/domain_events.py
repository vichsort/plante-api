from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.value_objects.ids import UserPlantId
from src.modules.catalog import PlantSpeciesId
from src.shared.domain import DomainEvent, UserId


@dataclass(frozen=True)
class StreakBrokenEvent(DomainEvent):
    user_id: UserId
    user_plant_id: UserPlantId
    last_streak_count: int

    @classmethod
    def create(cls, user_id: UserId, user_plant_id: UserPlantId, last_count: int) -> 'StreakBrokenEvent':
        return cls(
            occurred_on=datetime.now(UTC),
            user_id=user_id,
            user_plant_id=user_plant_id,
            last_streak_count=last_count
        )

@dataclass(frozen=True)
class PlantAddedToGardenEvent(DomainEvent):
    user_id: UserId
    user_plant_id: UserPlantId
    species_id: PlantSpeciesId
    is_first_plant: bool

    @classmethod
    def create(
        cls,
        user_id: UserId,
        user_plant_id: UserPlantId,
        species_id: PlantSpeciesId,
        is_first_plant: bool,
    ) -> "PlantAddedToGardenEvent":
        return cls(
            occurred_on=datetime.now(UTC),
            user_id=user_id,
            user_plant_id=user_plant_id,
            species_id=species_id,
            is_first_plant=is_first_plant,
        )

@dataclass(frozen=True)
class PlantWateredEvent(DomainEvent):
    user_id: UserId
    user_plant_id: UserPlantId
    current_streak: int

    @classmethod
    def create(
        cls, 
        user_id: UserId, 
        user_plant_id: UserPlantId, 
        current_streak: int
    ) -> 'PlantWateredEvent':
        return cls(
            occurred_on=datetime.now(UTC),
            user_id=user_id,
            user_plant_id=user_plant_id,
            current_streak=current_streak,
        )