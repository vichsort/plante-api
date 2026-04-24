from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from enum import Enum
from src.domain.value_objects.user_location import UserLocation
from src.domain.value_objects.geo_coordinates import GeoCoordinates

class WeatherSeverity(Enum):
    NORMAL = "normal"
    ATTENTION = "attention"     # calor ou frio moderado, chuva acima do normal
    CRITICAL = "critical"       # geada, seca extrema, tempestade

@dataclass(frozen=True)
class DailyWeather:
    date: date
    temperature_max: float
    temperature_min: float
    precipitation_mm: float
    humidity_percent: float
    severity: WeatherSeverity


@dataclass(frozen=True)
class WeatherContext:
    location: UserLocation | GeoCoordinates
    recent_days: tuple[DailyWeather, ...]
    forecast_days: tuple[DailyWeather, ...]
    has_critical_event: bool

    @property
    def recent_precipitation_total(self) -> float:
        return sum(d.precipitation_mm for d in self.recent_days)

    @property
    def avg_temperature(self) -> float:
        if not self.recent_days:
            return 0.0
        return sum(d.temperature_max for d in self.recent_days) / len(self.recent_days)


class IWeatherService(ABC):
    @abstractmethod
    async def get_context(
        self,
        location: UserLocation | GeoCoordinates,
        recent_days: int = 0,
        forecast_days: int = 7,
    ) -> WeatherContext: 
        """
        Retorna contexto climático de uma região.
        Usado para ajustar rega, diagnosticar saúde e emitir alertas.
        """
        ...