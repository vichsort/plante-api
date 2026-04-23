from dataclasses import dataclass
from datetime import datetime, timedelta, date, timezone

@dataclass(frozen=True)
class Streak:
    current_count: int
    last_action_time: datetime | None = None

    def __post_init__(self) -> None:
        if self.current_count < 0:
            raise ValueError("Streak count cannot be negative.")
        if self.last_action_time is not None and self.last_action_time.tzinfo is None:
            raise ValueError("last_action_time must be timezone-aware.")

    def _get_domain_date(self, dt: datetime) -> date:
        """Dia vira às 08:00 — 07:59 ainda conta como dia anterior."""
        return (dt - timedelta(hours=8)).date()

    def register_action(self, action_time: datetime) -> "Streak":
        if action_time.tzinfo is None:
            raise ValueError("action_time must be timezone-aware.")

        if self.last_action_time is None:
            return Streak(current_count=1, last_action_time=action_time)

        delta_days = (
            self._get_domain_date(action_time)
            - self._get_domain_date(self.last_action_time)
        ).days

        if delta_days == 0:
            return self
        elif delta_days == 1:
            return Streak(current_count=self.current_count + 1, last_action_time=action_time)
        else:
            return Streak(current_count=1, last_action_time=action_time)