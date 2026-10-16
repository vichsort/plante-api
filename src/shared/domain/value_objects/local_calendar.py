from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class LocalCalendar:
    """
    Que dia é para o usuário. Rega, sequência e cota diária de tokens contam dias do calendário
    local, não de UTC: uma rega às 22h em Brasília é do mesmo dia, embora já seja o dia seguinte
    em UTC. Fuso único por enquanto (`LOCAL_TIMEZONE`); fuso por usuário quando o app sair do Brasil.
    """
    timezone: ZoneInfo

    @classmethod
    def from_name(cls, name: str) -> "LocalCalendar":
        return cls(timezone=ZoneInfo(name))

    def date_of(self, instant: datetime) -> date:
        if instant.tzinfo is None:
            raise ValueError("instant must be timezone-aware.")
        return instant.astimezone(self.timezone).date()
