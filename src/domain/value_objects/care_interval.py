from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta

MAX_INTERVAL_DAYS = 365

@dataclass(frozen=True)
class CareInterval:
    days: int

    def __post_init__(self) -> None:
        if not isinstance(self.days, int) or self.days <= 0:
            raise ValueError(f"Care interval must be at least 1 day. Got: {self.days}")
        if self.days > MAX_INTERVAL_DAYS:
            raise ValueError(f"Care interval cannot exceed {MAX_INTERVAL_DAYS} days. Got: {self.days}")

    def calculate_next_due_date(self, actual_action_date: date) -> datetime:
        """Retorna datetime aware (UTC) para comparação homogênea com is_overdue."""
        next_date = actual_action_date + timedelta(days=self.days)
        return datetime(next_date.year, next_date.month, next_date.day, tzinfo=timezone.utc)