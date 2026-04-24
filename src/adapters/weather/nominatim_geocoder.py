import httpx
import structlog
from src.domain.value_objects.user_location import UserLocation
from src.domain.value_objects.geo_coordinates import GeoCoordinates

log = structlog.get_logger()

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Obrigatório pelo ToS da OSM — identifica sua aplicação
_HEADERS = {"User-Agent": "PlantE/2.0 (contact@plante.app)"}


class NominatimGeocoder:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def resolve(self, location: UserLocation) -> GeoCoordinates:
        params = {
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
            raise GeocodingError(f"No results for location: {location}")

        first = results[0]
        coords = GeoCoordinates(
            latitude=float(first["lat"]),
            longitude=float(first["lon"]),
        )
        log.debug("geocoding.resolved", lat=coords.latitude, lon=coords.longitude)
        return coords

class GeocodingError(Exception):
    pass