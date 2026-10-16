from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import StrEnum

from src.domain.entities.care_schedule import CareSchedule
from src.domain.exceptions import PlantNotReadyForWateringError
from src.domain.value_objects.garden_calendar import GardenCalendar
from src.domain.value_objects.ids import IdentificationId, UserId, UserPlantId
from src.domain.value_objects.streak import Streak


class IdentificationStatus(StrEnum):
    PENDING_ENRICHMENT = "pending_enrichment"
    IDENTIFIED = "identified"
    ENRICHED = "enriched"

class IdentificationSource(StrEnum):
    KINDWISE = "kindwise"
    PLANTNET = "plantnet"
    CONSENSUS = "consensus"

@dataclass(slots=True)
class UserPlant:
    id: UserPlantId
    user_id: UserId
    scientific_name: str
    identification_confidence: float
    identification_source: IdentificationSource
    status: IdentificationStatus
    care_schedule: CareSchedule
    # Identificação que originou a planta: só entra no jardim a partir de uma identificação
    identification_id: IdentificationId
    added_at: datetime | None = None

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

    def needs_watering(self, today: date) -> bool:
        """A janela da próxima rega já abriu (planta nunca regada não tem vencimento: não cobra)."""
        schedule = self.care_schedule
        return schedule.next_due_on is not None and schedule.is_window_open(today)

    def next_watering_on(self, calendar: GardenCalendar) -> date | None:
        """Primeiro dia em que a próxima rega é aceita (None: qualquer dia). Uma rega por dia."""
        opens_on = self.care_schedule.window_opens_on
        if self.last_watered_at is None:
            return opens_on
        day_after_last = calendar.date_of(self.last_watered_at) + timedelta(days=1)
        return day_after_last if opens_on is None else max(opens_on, day_after_last)

    def water(self, action_time: datetime, calendar: GardenCalendar) -> None:
        today = calendar.date_of(action_time)
        earliest = self.next_watering_on(calendar)
        if earliest is not None and today < earliest:
            raise PlantNotReadyForWateringError(next_date=earliest.strftime("%d/%m/%Y"))

        on_time = not self.care_schedule.is_missed(today)
        self.watering_streak = self.watering_streak.register_action(action_time, on_time=on_time)
        self.care_schedule = self.care_schedule.complete(action_time, completed_on=today)
        self.last_watered_at = action_time

    def break_streak_if_missed(self, today: date) -> bool:
        """Chamado pelo cron diário. True se a sequência foi quebrada agora."""
        if self.watering_streak.current_count == 0 or not self.care_schedule.is_missed(today):
            return False
        self.watering_streak = self.watering_streak.broken()
        return True


@dataclass(frozen=True)
class GardenPlant:
    """A planta como o jardim mostra hoje: se precisa de rega depende do dia local, não só do estado salvo."""
    plant: UserPlant
    needs_watering: bool

    @classmethod
    def of(cls, plant: UserPlant, today: date) -> "GardenPlant":
        return cls(plant=plant, needs_watering=plant.needs_watering(today))
