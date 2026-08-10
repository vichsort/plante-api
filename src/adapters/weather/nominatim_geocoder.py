from typing import Any

import httpx
import structlog

from src.domain.exceptions import ExternalServiceError
from src.domain.value_objects.geo_coordinates import GeoCoordinates
from src.domain.value_objects.user_location import UserLocation

log = structlog.get_logger()

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "PlantE/2.0 (contact@plante.app)"}


class GeocodingError(ExternalServiceError):
    """Exceção levantada quando ocorre um erro de geocodificação."""
    pass


class NominatimGeocoder:
    _client: httpx.AsyncClient

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def resolve(self, location: UserLocation) -> GeoCoordinates:
        params: dict[str, Any] = {
            "q": f"{location.state}, {location.country}",
            "format": "json",
            "limit": 1,
        }
        log.debug("geocoding.request", query=params["q"])

        response = await self._client.get(
            _NOMINATIM_URL, params=params, headers=_HEADERS, timeout=5.0
        )
        response.raise_for_status()

        results = response.json()
        if not results:
            raise GeocodingError(message=f"No results for location: {location}")

        first = results[0]
        coords = GeoCoordinates(
            latitude=float(first["lat"]),
            longitude=float(first["lon"]),
        )
        log.debug("geocoding.resolved", lat=coords.latitude, lon=coords.longitude)
        return coords