import structlog
from redis.asyncio import Redis
from src.domain.ports.token_repository import ITokenRepository

log = structlog.get_logger()

_KEY = "refresh:{user_id}"

class RedisTokenRepository(ITokenRepository):
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, user_id: int) -> str:
        return _KEY.format(user_id=user_id)

    async def save_refresh_token(
        self,
        user_id: int,
        token: str,
        ttl_seconds: int,
    ) -> None:
        key = self._key(user_id)
        await self._redis.set(key, token, ex=ttl_seconds)
        log.debug("token.saved", user_id=user_id, ttl=ttl_seconds)

    async def get_refresh_token(self, user_id: int) -> str | None:
        key = self._key(user_id)
        value = await self._redis.get(key)
        return value.decode() if value else None

    async def delete_refresh_token(self, user_id: int) -> None:
        key = self._key(user_id)
        await self._redis.delete(key)
        log.debug("token.deleted", user_id=user_id)