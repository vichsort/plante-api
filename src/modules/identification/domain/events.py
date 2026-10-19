from dataclasses import dataclass
from datetime import UTC, datetime

from src.modules.catalog import PlantSpeciesId
from src.shared.domain import DomainEvent, UserId


@dataclass(frozen=True)
class PlantIdentifiedEvent(DomainEvent):
    """Publicado depois do commit de cada identificação. Ninguém consome ainda (conquistas, depois)."""
    user_id: UserId
    species_id: PlantSpeciesId
    is_first_plant: bool

    @classmethod
    def create(cls, user_id: UserId, species_id: PlantSpeciesId, is_first_plant: bool) -> "PlantIdentifiedEvent":
        return cls(
            occurred_on=datetime.now(UTC),
            user_id=user_id,
            species_id=species_id,
            is_first_plant=is_first_plant,
        )
