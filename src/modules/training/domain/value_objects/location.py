from dataclasses import dataclass
from datetime import date, datetime

# 1 casa decimal ≈ 11 km: mostra em que região uma planta é comum sem apontar uma casa
_GRID_DECIMALS = 1


@dataclass(frozen=True)
class TrainingLocation:
    """Localização aproximada de uma amostra de treino: estado do perfil + grade de ~11 km."""
    country: str
    state: str
    grid_latitude: float | None = None
    grid_longitude: float | None = None

    def __post_init__(self) -> None:
        if (self.grid_latitude is None) != (self.grid_longitude is None):
            raise ValueError("grid_latitude and grid_longitude must be both set or both empty.")

    @classmethod
    def coarse(
        cls, country: str, state: str, latitude: float | None, longitude: float | None,
    ) -> "TrainingLocation":
        """
        Estado do perfil + a célula da grade. O GPS exato nunca é guardado, e a grade só entra
        quando vierem as duas coordenadas.
        """
        if latitude is None or longitude is None:
            return cls(country=country, state=state)
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            raise ValueError("Coordinates out of range.")
        return cls(
            country=country,
            state=state,
            grid_latitude=round(latitude, _GRID_DECIMALS),
            grid_longitude=round(longitude, _GRID_DECIMALS),
        )


def month_of(moment: datetime) -> date:
    """Período de uma amostra de treino: só o mês (o horário exato não entra no dataset)."""
    return date(moment.year, moment.month, 1)
