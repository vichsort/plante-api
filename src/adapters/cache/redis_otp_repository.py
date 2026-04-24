from redis.asyncio import Redis
from src.domain.ports.otp_repository import IOtpRepository

class RedisOtpRepository(IOtpRepository):
    _KEY_PREFIX = "otp:"

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def _key(self, user_id: int) -> str:
        return f"{self._KEY_PREFIX}{user_id}"

    async def save_code(self, user_id: int, code: str, expires_in_minutes: int = 15) -> None:
        await self._redis.set(
            self._key(user_id),
            code,
            ex=expires_in_minutes * 60,
        )

    async def get_active_code_for_user(self, user_id: int) -> str | None:
        value = await self._redis.get(self._key(user_id))
        return value.decode() if value else None

    async def consume_code(self, user_id: int) -> None:
        await self._redis.delete(self._key(user_id))