from src.modules.identity.domain.ports.otp_repository import IOtpRepository
from src.shared.adapters import RedisClient
from src.shared.domain import UserId


class RedisOtpRepository(IOtpRepository):
    _KEY_PREFIX = "otp:"

    def __init__(self, redis: RedisClient) -> None:
        self._redis = redis

    def _key(self, user_id: UserId) -> str:
        return f"{self._KEY_PREFIX}{user_id}"

    async def save_code(self, user_id: UserId, code: str, expires_in_minutes: int = 15) -> None:
        await self._redis.set(self._key(user_id), code, ttl_seconds=expires_in_minutes * 60)

    async def get_active_code_for_user(self, user_id: UserId) -> str | None:
        value = await self._redis.get(self._key(user_id))
        return value.decode() if value else None

    async def consume_code(self, user_id: UserId) -> None:
        await self._redis.delete(self._key(user_id))
