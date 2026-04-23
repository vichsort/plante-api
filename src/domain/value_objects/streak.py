from dataclasses import dataclass
from datetime import datetime, timedelta, date

@dataclass(frozen=True)
class Streak:
    current_count: int
    last_action_time: datetime | None = None

    def __post_init__(self):
        if self.current_count < 0:
            raise ValueError("Streak count cannot be negative.")

    def _get_domain_date(self, dt: datetime) -> date:
        """
        Aplica a regra de carência: o 'dia' só vira às 08:00:00.
        Subtraindo 8 horas, 07:59am de hoje conta como o dia de ontem.
        """
        shifted_dt = dt - timedelta(hours=8)
        return shifted_dt.date()

    def register_action(self, action_time: datetime) -> 'Streak':
        """Calcula o novo Streak baseado na ação atual."""
        if self.last_action_time is None:
            return Streak(current_count=1, last_action_time=action_time)

        last_date = self._get_domain_date(self.last_action_time)
        current_date = self._get_domain_date(action_time)
        delta_days = (current_date - last_date).days

        if delta_days == 0:
            # Já regou hoje, mantém o streak atual
            return self
        elif delta_days == 1:
            # Regou no dia seguinte certinho, incrementa
            return Streak(current_count=self.current_count + 1, last_action_time=action_time)
        else:
            # Quebrou a ofensiva. Reinicia o contador.
            return Streak(current_count=1, last_action_time=action_time)