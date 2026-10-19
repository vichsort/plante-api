from dataclasses import dataclass
from datetime import date, timedelta

MAX_INTERVAL_DAYS = 365

@dataclass(frozen=True)
class CareInterval:
    days: int

    def __post_init__(self) -> None:
        if not isinstance(self.days, int) or self.days <= 0:
            raise ValueError(f"Care interval must be at least 1 day. Got: {self.days}")
        if self.days > MAX_INTERVAL_DAYS:
            raise ValueError(f"Care interval cannot exceed {MAX_INTERVAL_DAYS} days. Got: {self.days}")

    def calculate_next_due_date(self, actual_action_date: date) -> date:
        return actual_action_date + timedelta(days=self.days)
