import json
from uuid import uuid4

import httpx
import pytest

from src.adapters.cache.redis_health_raw_response_repository import (
    RedisHealthRawResponseRepository,
)
from src.adapters.weather.nominatim_geocoder import NominatimGeocoder
from src.adapters.weather.open_meteo_adapter import OpenMeteoAdapter
from src.domain.exceptions import ExternalServiceError, GeocodingError
from src.domain.ports.health_raw_response_repository import PendingHealthAssessment
from src.domain.ports.weather_service import WeatherSeverity
from src.domain.value_objects.geo_coordinates import GeoCoordinates
from src.domain.value_objects.ids import HealthRecordId
from src.domain.value_objects.user_location import UserLocation


class _MemoryRedis:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes | None:
        return self.values.get(key)

    async def set(self, key: str, value: str | bytes, ttl_seconds: int) -> None:
        self.values[key] = value.encode() if isinstance(value, str) else value

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)


@pytest.mark.asyncio
async def test_pending_health_assessment_round_trip():
    redis = _MemoryRedis()
    repo = RedisHealthRawResponseRepository(redis)
    record_id = HealthRecordId(uuid4())
    assessment = PendingHealthAssessment(raw_response={"result": {"is_plant": True}}, similar_images_urls=("u1",))

    await repo.save(record_id, assessment)
    assert await repo.get(record_id) == assessment

    await repo.delete(record_id)
    assert await repo.get(record_id) is None


@pytest.mark.asyncio
async def test_pending_health_assessment_in_unknown_format_counts_as_expired():
    redis = _MemoryRedis()
    repo = RedisHealthRawResponseRepository(redis)
    record_id = HealthRecordId(uuid4())
    redis.values[f"health_raw:{record_id}"] = json.dumps({"result": {}}).encode()  # formato antigo: só o raw

    assert await repo.get(record_id) is None


def _client(body: object) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)))


@pytest.mark.asyncio
async def test_open_meteo_parses_days_with_missing_measurements():
    forecast = {"daily": {
        "time": ["2026-10-15", "2026-10-16"],
        "weathercode": [95, None],
        "temperature_2m_max": [30.5, None],
        "temperature_2m_min": [18.0, 17.5],
        "precipitation_sum": [12.0, None],
        "relativehumidity_2m_max": [90.0, 80.0],
    }}
    adapter = OpenMeteoAdapter(client=_client(forecast), geocoder=NominatimGeocoder(_client([])))

    context = await adapter.get_context(GeoCoordinates(latitude=-27.6, longitude=-48.5))

    assert [day.severity for day in context.forecast_days] == [WeatherSeverity.CRITICAL, WeatherSeverity.NORMAL]
    assert context.forecast_days[1].temperature_max == 0.0
    assert context.has_critical_event is True


@pytest.mark.asyncio
async def test_open_meteo_rejects_unexpected_format():
    adapter = OpenMeteoAdapter(client=_client({"daily": {"time": "today"}}), geocoder=NominatimGeocoder(_client([])))
    with pytest.raises(ExternalServiceError):
        await adapter.get_context(GeoCoordinates(latitude=0.0, longitude=0.0))


@pytest.mark.asyncio
async def test_nominatim_resolves_text_coordinates():
    geocoder = NominatimGeocoder(_client([{"lat": "-27.59", "lon": "-48.54", "display_name": "SC"}]))
    coords = await geocoder.resolve(UserLocation(country="BR", state="Santa Catarina"))
    assert (coords.latitude, coords.longitude) == (-27.59, -48.54)


@pytest.mark.asyncio
async def test_nominatim_without_results_is_geocoding_error():
    with pytest.raises(GeocodingError):
        await NominatimGeocoder(_client([])).resolve(UserLocation(country="BR", state="Atlantis"))
