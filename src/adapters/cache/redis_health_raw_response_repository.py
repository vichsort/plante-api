import json
from redis.asyncio import Redis
from src.domain.ports.health_raw_response_repository import IHealthRawResponseRepository

_KEY_PREFIX = "health_raw:"
_TTL_SECONDS = 60 * 60 * 24  # 24 horas

class RedisHealthRawResponseRepository(IHealthRawResponseRepository):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, health_record_id: int) -> str:
        return f"{_KEY_PREFIX}{health_record_id}"

    async def save(self, health_record_id: int, raw_response: dict) -> None:
        await self._redis.set(
            self._key(health_record_id),
            json.dumps(raw_response),
            ex=_TTL_SECONDS,
        )

    async def get(self, health_record_id: int) -> dict | None:
        value = await self._redis.get(self._key(health_record_id))
        return json.loads(value) if value else None

    async def delete(self, health_record_id: int) -> None:
        await self._redis.delete(self._key(health_record_id))