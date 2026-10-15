from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from enum import Enum
from typing import Any

from src.domain.value_objects.care_interval import CareInterval


class CareType(Enum):
    WATER = "water"
    PRUNE = "prune"
    FERTILIZE = "fertilize"
    REPOT = "repot"
    TREAT = "treat" 

@dataclass(frozen=True)
class CareSchedule:
    id: Any
    user_plant_id: Any
    care_type: CareType
    interval: CareInterval
    is_active: bool
    created_at: datetime | None = None

    next_due_at: datetime | None = None
    last_completed_at: datetime | None = None
    climate_adjusted: bool = False

    def __post_init__(self) -> None:
        if self.climate_adjusted and not self.last_completed_at:
            raise ValueError(
                "climate_adjusted só pode ser True se houve ao menos uma execução."
            )

    def is_overdue(self, current_time: datetime) -> bool:
        if self.next_due_at is None:
            return False
        next_due = (
            datetime.combine(self.next_due_at, time.min, tzinfo=UTC)
            if isinstance(self.next_due_at, date) and not isinstance(self.next_due_at, datetime)
            else self.next_due_at
        )
        if next_due.tzinfo is None:
            next_due = next_due.replace(tzinfo=UTC)
        curr_time = current_time.replace(tzinfo=UTC) if current_time.tzinfo is None else current_time
        return curr_time > next_due

    def complete(self, completed_at: datetime) -> "CareSchedule":
        if completed_at.tzinfo is None:
            raise ValueError("completed_at must be timezone-aware.")
        next_due = self.interval.calculate_next_due_date(completed_at.date())
        return CareSchedule(
            id=self.id,
            user_plant_id=self.user_plant_id,
            care_type=self.care_type,
            interval=self.interval,
            is_active=self.is_active,
            created_at=self.created_at,
            next_due_at=next_due,
            last_completed_at=completed_at,
            climate_adjusted=self.climate_adjusted,
        )