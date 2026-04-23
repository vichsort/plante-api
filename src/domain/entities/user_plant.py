from dataclasses import dataclass, field
from datetime import datetime
from src.domain.value_objects.streak import Streak
from enum import Enum

class IdentificationStatus(Enum):
    IDENTIFIED = "identified"
    PENDING_ENRICHMENT = "pending_enrichment"
    ENRICHED = "enriched"


@dataclass(frozen=True)
class UserPlant:
    id: int
    user_id: int
    scientific_name: str        # referência à PlantSpecies
    identification_confidence: float
    identification_source: str  # "kindwise" | "plantnet"
    status: IdentificationStatus
    added_at: datetime

    nickname: str | None = None
    primary_image_url: str | None = None
    watering_streak: Streak = field(default_factory=lambda: Streak(current_count=0))
    last_watered_at: datetime | None = None
    next_watering_at: datetime | None = None

    def __post_init__(self):
        if not 0.0 <= self.identification_confidence <= 1.0:
            raise ValueError("identification_confidence needs to be between 0.0 and 1.0.")
        if not self.scientific_name:
            raise ValueError("scientific_name cannot be null.")

    @property
    def display_name(self) -> str:
        """Nome de exibição: apelido do usuário ou nome científico."""
        return self.nickname or self.scientific_name

    @property
    def needs_watering(self) -> bool:
        """Verifica se a planta precisa ser regada hoje."""
        if self.next_watering_at is None:
            return False
        return datetime.utcnow() >= self.next_watering_at