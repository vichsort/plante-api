from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from src.domain.entities.care_schedule import CareSchedule
from src.domain.exceptions import PlantNotReadyForWateringError
from src.domain.value_objects.streak import Streak

class IdentificationStatus(Enum):
    PENDING_ENRICHMENT = "pending_enrichment"
    IDENTIFIED = "identified"
    ENRICHED = "enriched"

class IdentificationSource(Enum):
    KINDWISE = "kindwise"
    PLANTNET = "plantnet"
    CONSENSUS = "consensus"

@dataclass(slots=True)
class UserPlant:
    id: int | None
    user_id: int
    scientific_name: str
    identification_confidence: float
    identification_source: IdentificationSource
    status: IdentificationStatus
    added_at: datetime
    care_schedule: CareSchedule

    nickname: str | None = None
    primary_image_url: str | None = None
    last_watered_at: datetime | None = None
    watering_streak: Streak = field(default_factory=lambda: Streak(current_count=0))

    def __post_init__(self) -> None:
        if not self.scientific_name:
            raise ValueError("scientific_name cannot be empty.")
        if not 0.0 <= self.identification_confidence <= 1.0:
            raise ValueError("identification_confidence must be between 0.0 and 1.0.")

    @property
    def display_name(self) -> str:
        return self.nickname or self.scientific_name

    @property
    def needs_watering(self) -> bool:
        return self.care_schedule.is_overdue(datetime.now(timezone.utc))

    def water(self, action_time: datetime) -> None:
        if (
            self.care_schedule.next_due_at
            and action_time < self.care_schedule.next_due_at
        ):
            raise PlantNotReadyForWateringError(
                next_date=self.care_schedule.next_due_at.strftime("%d/%m/%Y")
            )

        self.watering_streak = self.watering_streak.register_action(action_time)
        self.care_schedule = self.care_schedule.complete(action_time)
        self.last_watered_at = action_time

    def check_and_reset_streak(self, current_time: datetime) -> bool:
        """Chamado pelo worker diário. Retorna True se o streak foi resetado."""
        if self.watering_streak.current_count <= 1:
            return False

        if self.care_schedule.is_overdue(current_time):
            self.watering_streak = Streak(
                current_count=1,
                last_action_time=self.watering_streak.last_action_time,
            )
            return True

        return False