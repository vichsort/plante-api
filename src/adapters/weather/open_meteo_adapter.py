from datetime import date

import httpx
import structlog
from pydantic import BaseModel, ConfigDict, ValidationError

from src.adapters.weather.nominatim_geocoder import NominatimGeocoder
from src.domain.exceptions import ExternalServiceError, GeocodingError
from src.domain.ports.weather_service import (
    DailyWeather,
    IWeatherService,
    WeatherContext,
    WeatherSeverity,
)
from src.domain.value_objects.geo_coordinates import GeoCoordinates
from src.domain.value_objects.user_location import UserLocation

log = structlog.stdlib.get_logger()

_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_CRITICAL_CODES = frozenset({
    71, 73, 75, 77,
    85, 86,
    95, 96, 99,
})
_ATTENTION_CODES = frozenset({
    51, 53, 55,
    61, 63, 65,
    80, 81, 82,
})

class _Daily(BaseModel):
    """Séries diárias do Open-Meteo: listas paralelas, com `null` quando falta a medição."""
    model_config = ConfigDict(frozen=True)

    time: list[date]
    weathercode: list[int | None]
    temperature_2m_max: list[float | None]
    temperature_2m_min: list[float | None]
    precipitation_sum: list[float | None]
    relativehumidity_2m_max: list[float | None]


class _Forecast(BaseModel):
    model_config = ConfigDict(frozen=True)

    daily: _Daily


def _wmo_to_severity(code: int | None) -> WeatherSeverity:
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
        days = self._parse_days(await self._fetch_forecast(coords, forecast_days))

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

    async def _fetch_forecast(self, coords: GeoCoordinates, forecast_days: int) -> _Forecast:
        params: dict[str, str | int | float | list[str]] = {
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
        try:
            return _Forecast.model_validate_json(response.content)
        except ValidationError as exc:
            raise ExternalServiceError(message="Unexpected response format.", service="OpenMeteo") from exc

    def _parse_days(self, forecast: _Forecast) -> list[DailyWeather]:
        daily = forecast.daily
        return [
            DailyWeather(
                date=day,
                temperature_max=daily.temperature_2m_max[i] or 0.0,
                temperature_min=daily.temperature_2m_min[i] or 0.0,
                precipitation_mm=daily.precipitation_sum[i] or 0.0,
                humidity_percent=daily.relativehumidity_2m_max[i] or 0.0,
                severity=_wmo_to_severity(daily.weathercode[i]),
            )
            for i, day in enumerate(daily.time)
        ]
