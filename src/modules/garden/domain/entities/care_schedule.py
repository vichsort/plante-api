from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

from src.modules.garden.domain.value_objects.care_interval import CareInterval


class CareType(StrEnum):
    WATER = "water"
    PRUNE = "prune"
    FERTILIZE = "fertilize"
    REPOT = "repot"
    TREAT = "treat" 

# Tolerância em volta do vencimento: regar um dia antes ou um dia depois ainda conta como no prazo
WINDOW_DAYS = 1


@dataclass(frozen=True)
class CareSchedule:
    """
    Rotina de cuidado de uma planta. Não tem identidade própria: pertence ao `UserPlant`.

    O vencimento é um dia do calendário local (`LocalCalendar`), não um instante. A janela do
    cuidado vai de `WINDOW_DAYS` antes a `WINDOW_DAYS` depois do vencimento: antes dela é cedo
    demais; depois dela o cuidado foi perdido. Sem vencimento (nunca feito), vale a qualquer dia.
    """
    care_type: CareType
    interval: CareInterval
    is_active: bool
    created_at: datetime | None = None

    next_due_on: date | None = None
    last_completed_at: datetime | None = None
    climate_adjusted: bool = False

    def __post_init__(self) -> None:
        if self.climate_adjusted and not self.last_completed_at:
            raise ValueError(
                "climate_adjusted só pode ser True se houve ao menos uma execução."
            )

    @property
    def window_opens_on(self) -> date | None:
        if self.next_due_on is None:
            return None
        return self.next_due_on - timedelta(days=WINDOW_DAYS)

    def is_window_open(self, today: date) -> bool:
        """Já pode fazer (inclui atrasado)."""
        return self.window_opens_on is None or today >= self.window_opens_on

    def is_missed(self, today: date) -> bool:
        """A janela inteira passou sem o cuidado."""
        if self.next_due_on is None:
            return False
        return today > self.next_due_on + timedelta(days=WINDOW_DAYS)

    @staticmethod
    def missed_if_due_before(today: date) -> date:
        """Vencimentos anteriores a esta data já tiveram a janela inteira perdida em `today`."""
        return today - timedelta(days=WINDOW_DAYS)

    def complete(self, completed_at: datetime, completed_on: date) -> "CareSchedule":
        if completed_at.tzinfo is None:
            raise ValueError("completed_at must be timezone-aware.")
        return CareSchedule(
            care_type=self.care_type,
            interval=self.interval,
            is_active=self.is_active,
            created_at=self.created_at,
            next_due_on=self.interval.calculate_next_due_date(completed_on),
            last_completed_at=completed_at,
            climate_adjusted=self.climate_adjusted,
        )
