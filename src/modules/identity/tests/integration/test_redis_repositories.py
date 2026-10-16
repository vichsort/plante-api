"""Repositórios de cache contra um Redis real: chaves, TTL e formato gravado."""
from uuid import uuid4

from redis.asyncio import Redis

from src.modules.identity.adapters.redis.otp_repository import RedisOtpRepository
from src.modules.identity.adapters.redis.token_repository import RedisTokenRepository
from src.shared.adapters import RedisClient
from src.shared.domain import UserId


def _user_id() -> UserId:
    return UserId(uuid4())


async def test_otp_lifecycle(redis_client: RedisClient, raw_redis: Redis) -> None:
    # Arrange
    repo = RedisOtpRepository(redis_client)
    user_id = _user_id()

    # Act
    await repo.save_code(user_id, "123456", expires_in_minutes=15)

    # Assert
    assert await repo.get_active_code_for_user(user_id) == "123456"
    assert 14 * 60 < await raw_redis.ttl(f"otp:{user_id}") <= 15 * 60
    await repo.consume_code(user_id)
    assert await repo.get_active_code_for_user(user_id) is None


async def test_otp_new_code_replaces_previous(redis_client: RedisClient) -> None:
    # Arrange
    repo = RedisOtpRepository(redis_client)
    user_id = _user_id()

    # Act
    await repo.save_code(user_id, "111111")
    await repo.save_code(user_id, "222222")

    # Assert
    assert await repo.get_active_code_for_user(user_id) == "222222"


async def test_otp_is_scoped_by_user(redis_client: RedisClient) -> None:
    # Arrange
    repo = RedisOtpRepository(redis_client)

    # Act
    await repo.save_code(_user_id(), "123456")

    # Assert
    assert await repo.get_active_code_for_user(_user_id()) is None


async def test_refresh_token_lifecycle(redis_client: RedisClient, raw_redis: Redis) -> None:
    # Arrange
    repo = RedisTokenRepository(redis_client)
    user_id = _user_id()

    # Act
    await repo.save_refresh_token(user_id, "refresh.jwt.token", ttl_seconds=3600)

    # Assert
    assert await repo.get_refresh_token(user_id) == "refresh.jwt.token"
    assert 0 < await raw_redis.ttl(f"refresh:{user_id}") <= 3600
    await repo.delete_refresh_token(user_id)
    assert await repo.get_refresh_token(user_id) is None
