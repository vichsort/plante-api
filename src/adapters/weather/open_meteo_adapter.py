import httpx
import structlog
from datetime import date

from src.domain.ports.weather_service import (
    IWeatherService,
    DailyWeather,
    WeatherContext,
    WeatherSeverity,
)
from src.domain.value_objects.user_location import UserLocation
from src.domain.value_objects.geo_coordinates import GeoCoordinates
from src.adapters.weather.nominatim_geocoder import NominatimGeocoder, GeocodingError

log = structlog.get_logger()

_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO Weather Interpretation Codes
# https://open-meteo.com/en/docs#weathervariables
_CRITICAL_CODES = frozenset({
    71, 73, 75, 77,          # neve moderada/intensa
    85, 86,                  # neve em rajadas
    95, 96, 99,              # tempestades com granizo
})
_ATTENTION_CODES = frozenset({
    51, 53, 55,              # garoa
    61, 63, 65,              # chuva moderada/forte
    80, 81, 82,              # pancadas
})

def _wmo_to_severity(code: int) -> WeatherSeverity:
    if code in _CRITICAL_CODES:
        return WeatherSeverity.CRITICAL
    if code in _ATTENTION_CODES:
        return WeatherSeverity.ATTENTION
    return WeatherSeverity.NORMAL

class OpenMeteoAdapter(IWeatherService):
    def __init__(
        self,
        client: httpx.AsyncClient,
        geocoder: NominatimGeocoder,
    ) -> None:
        self._client = client
        self._geocoder = geocoder

    async def get_context(
        self,
        location: UserLocation | GeoCoordinates,
        recent_days: int = 0,
        forecast_days: int = 7,
    ) -> WeatherContext:
        coords = await self._resolve_coords(location)
        raw = await self._fetch_forecast(coords, forecast_days)
        days = self._parse_days(raw)

        has_critical = any(d.severity == WeatherSeverity.CRITICAL for d in days)

        return WeatherContext(
            location=location,
            recent_days=(),
            forecast_days=tuple(days),
            has_critical_event=has_critical,
        )

    async def _resolve_coords(
        self, location: UserLocation | GeoCoordinates
    ) -> GeoCoordinates:
        if isinstance(location, GeoCoordinates):
            return location
        try:
            return await self._geocoder.resolve(location)
        except GeocodingError:
            log.warning("weather.geocoding_failed", location=str(location))
            raise

    async def _fetch_forecast(
        self, coords: GeoCoordinates, forecast_days: int
    ) -> dict:
        params = {
            "latitude": coords.latitude,
            "longitude": coords.longitude,
            "daily": [
                "weathercode",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "relativehumidity_2m_max",
            ],
            "timezone": "auto",
            "forecast_days": forecast_days,
        }
        log.debug("weather.request", lat=coords.latitude, lon=coords.longitude)
        response = await self._client.get(_FORECAST_URL, params=params, timeout=8.0)
        response.raise_for_status()
        return response.json()

    def _parse_days(self, data: dict) -> list[DailyWeather]:
        daily = data["daily"]
        days = []
        for i, iso_date in enumerate(daily["time"]):
            code = daily["weathercode"][i]
            days.append(
                DailyWeather(
                    date=date.fromisoformat(iso_date),
                    temperature_max=daily["temperature_2m_max"][i] or 0.0,
                    temperature_min=daily["temperature_2m_min"][i] or 0.0,
                    precipitation_mm=daily["precipitation_sum"][i] or 0.0,
                    humidity_percent=daily["relativehumidity_2m_max"][i] or 0.0,
                    severity=_wmo_to_severity(code),
                )
            )
        return days