from datetime import date

from src.modules.quota.domain.ports.usage_counter import IUsageCounter
from src.shared.adapters import RedisClient

# Two days: the key outlives its day by one, so a call near midnight never loses its count
_TTL_SECONDS = 2 * 24 * 60 * 60


class RedisUsageCounter(IUsageCounter):
    def __init__(self, redis: RedisClient, name: str) -> None:
        self._redis = redis
        self._prefix = f"plante:usage:{name}:"

    async def increment(self, day: date) -> int:
        return await self._redis.increment_with_expiry(f"{self._prefix}{day.isoformat()}", _TTL_SECONDS)
