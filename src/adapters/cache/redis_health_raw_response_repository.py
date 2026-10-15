import structlog
from pydantic import BaseModel, ConfigDict, ValidationError

from src.adapters.cache.redis_client import RedisClient
from src.domain.ports.health_raw_response_repository import (
    IHealthRawResponseRepository,
    PendingHealthAssessment,
)
from src.domain.value_objects.ids import HealthRecordId
from src.domain.value_objects.json_value import JsonObject

log = structlog.stdlib.get_logger()

_KEY_PREFIX = "health_raw:"
_TTL_SECONDS = 60 * 60 * 24  # 24 horas


class _StoredAssessment(BaseModel):
    """Formato gravado no Redis; validado na leitura (o valor pode ter sido escrito por outra versão)."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    raw_response: JsonObject
    similar_images_urls: tuple[str, ...]


class RedisHealthRawResponseRepository(IHealthRawResponseRepository):
    def __init__(self, redis: RedisClient) -> None:
        self._redis = redis

    def _key(self, health_record_id: HealthRecordId) -> str:
        return f"{_KEY_PREFIX}{health_record_id}"

    async def save(self, health_record_id: HealthRecordId, assessment: PendingHealthAssessment) -> None:
        stored = _StoredAssessment(
            raw_response=assessment.raw_response,
            similar_images_urls=assessment.similar_images_urls,
        )
        await self._redis.set(self._key(health_record_id), stored.model_dump_json(), ttl_seconds=_TTL_SECONDS)

    async def get(self, health_record_id: HealthRecordId) -> PendingHealthAssessment | None:
        value = await self._redis.get(self._key(health_record_id))
        if value is None:
            return None
        try:
            stored = _StoredAssessment.model_validate_json(value)
        except ValidationError:
            # Gravado por outra versão (ex.: antes do deploy): tratado como expirado, o usuário refaz o diagnóstico
            log.warning("health_raw.unreadable", health_record_id=str(health_record_id))
            return None
        return PendingHealthAssessment(
            raw_response=stored.raw_response,
            similar_images_urls=stored.similar_images_urls,
        )

    async def delete(self, health_record_id: HealthRecordId) -> None:
        await self._redis.delete(self._key(health_record_id))
