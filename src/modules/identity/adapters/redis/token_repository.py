import structlog

from src.modules.identity.domain.ports.token_repository import ITokenRepository
from src.shared.adapters import RedisClient
from src.shared.domain import UserId

log = structlog.stdlib.get_logger()

_KEY = "refresh:{user_id}"

class RedisTokenRepository(ITokenRepository):
    def __init__(self, redis: RedisClient) -> None:
        self._redis = redis

    def _key(self, user_id: UserId) -> str:
        return _KEY.format(user_id=user_id)

    async def save_refresh_token(
        self,
        user_id: UserId,
        token: str,
        ttl_seconds: int,
    ) -> None:
        await self._redis.set(self._key(user_id), token, ttl_seconds=ttl_seconds)
        log.debug("token.saved", user_id=str(user_id), ttl=ttl_seconds)

    async def get_refresh_token(self, user_id: UserId) -> str | None:
        value = await self._redis.get(self._key(user_id))
        return value.decode() if value else None

    async def delete_refresh_token(self, user_id: UserId) -> None:
        await self._redis.delete(self._key(user_id))
        log.debug("token.deleted", user_id=str(user_id))
