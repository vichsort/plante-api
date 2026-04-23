from dataclasses import dataclass
from datetime import date, timedelta

@dataclass(frozen=True)
class CareInterval:
    days: int

    def __post_init__(self):
        """Um intervalo de rega não pode ser zero ou negativo."""
        if not isinstance(self.days, int) or self.days <= 0:
            raise ValueError(f"Care interval must be at least 1 day. Got: {self.days}")

    def calculate_next_due_date(self, actual_action_date: date) -> date:
        """Sempre calcula com base no dia real em que a ação ocorreu."""
        return actual_action_date + timedelta(days=self.days)