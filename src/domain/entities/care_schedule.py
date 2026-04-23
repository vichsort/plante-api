from dataclasses import dataclass
from datetime import datetime, timezone, time
from enum import Enum
from src.domain.value_objects.care_interval import CareInterval

class CareType(Enum):
    WATER = "water"
    PRUNE = "prune"
    FERTILIZE = "fertilize"
    REPOT = "repot"
    TREAT = "treat" 

@dataclass(frozen=True)
class CareSchedule:
    id: int
    user_plant_id: int
    care_type: CareType
    interval: CareInterval
    is_active: bool
    created_at: datetime

    next_due_at: datetime | None = None
    last_completed_at: datetime | None = None
    climate_adjusted: bool = False  # True quando o Celery ajustou pelo clima

    def __post_init__(self):
        if self.climate_adjusted and not self.last_completed_at:
            raise ValueError(
                "climate_adjusted só pode ser True se houve ao menos uma execução."
            )

    def is_overdue(self, current_time: datetime) -> bool:
        """Verifica se o cuidado está atrasado em relação a um tempo fornecido."""
        if self.next_due_at is None:
            return False
        return current_time > self.next_due_at

    def complete(self, completed_at: datetime) -> 'CareSchedule':
        """Registra a conclusão e calcula o próximo agendamento."""
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