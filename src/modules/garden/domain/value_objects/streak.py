from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Streak:
    """Regas seguidas feitas no prazo. Quem diz se a rega veio no prazo é o `CareSchedule`."""
    current_count: int
    last_action_time: datetime | None = None

    def __post_init__(self) -> None:
        if self.current_count < 0:
            raise ValueError("Streak count cannot be negative.")
        if self.last_action_time is not None and self.last_action_time.tzinfo is None:
            raise ValueError("last_action_time must be timezone-aware.")

    def register_action(self, action_time: datetime, on_time: bool) -> "Streak":
        if action_time.tzinfo is None:
            raise ValueError("action_time must be timezone-aware.")
        # Atrasada recomeça a contagem: ela mesma é a primeira da nova sequência
        count = self.current_count + 1 if on_time else 1
        return Streak(current_count=count, last_action_time=action_time)

    def broken(self) -> "Streak":
        return Streak(current_count=0, last_action_time=self.last_action_time)
