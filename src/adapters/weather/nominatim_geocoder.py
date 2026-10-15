import httpx
import structlog
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from src.domain.exceptions import GeocodingError
from src.domain.value_objects.geo_coordinates import GeoCoordinates
from src.domain.value_objects.user_location import UserLocation

log = structlog.stdlib.get_logger()

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "PlantE/2.0 (contact@plante.app)"}


class _Place(BaseModel):
    """Resultado do Nominatim (`format=json`): coordenadas vêm como texto."""
    model_config = ConfigDict(frozen=True)

    lat: float
    lon: float


_PLACES = TypeAdapter(list[_Place])


class NominatimGeocoder:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def resolve(self, location: UserLocation) -> GeoCoordinates:
        query = f"{location.state}, {location.country}"
        log.debug("geocoding.request", query=query)

        response = await self._client.get(
            _NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers=_HEADERS,
            timeout=5.0,
        )
        response.raise_for_status()

        try:
            places = _PLACES.validate_json(response.content)
        except ValidationError as exc:
            raise GeocodingError(message="Unexpected response format.") from exc
        if not places:
            raise GeocodingError(message=f"No results for location: {location}")

        coords = GeoCoordinates(latitude=places[0].lat, longitude=places[0].lon)
        log.debug("geocoding.resolved", lat=coords.latitude, lon=coords.longitude)
        return coords
