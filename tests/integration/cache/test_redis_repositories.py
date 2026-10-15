"""Repositórios de cache contra um Redis real: chaves, TTL e formato gravado."""
import uuid

from redis.asyncio import Redis

from src.adapters.cache.redis_client import RedisClient
from src.adapters.cache.redis_health_raw_response_repository import (
    RedisHealthRawResponseRepository,
)
from src.adapters.cache.redis_otp_repository import RedisOtpRepository
from src.adapters.cache.redis_token_repository import RedisTokenRepository
from src.domain.ports.health_raw_response_repository import PendingHealthAssessment
from src.domain.value_objects.ids import HealthRecordId, UserId


def _user_id() -> UserId:
    return UserId(uuid.uuid4())


async def test_otp_lifecycle(redis_client: RedisClient, raw_redis: Redis) -> None:
    repo = RedisOtpRepository(redis_client)
    user_id = _user_id()

    await repo.save_code(user_id, "123456", expires_in_minutes=15)

    assert await repo.get_active_code_for_user(user_id) == "123456"
    assert 14 * 60 < await raw_redis.ttl(f"otp:{user_id}") <= 15 * 60

    await repo.consume_code(user_id)
    assert await repo.get_active_code_for_user(user_id) is None


async def test_otp_new_code_replaces_previous(redis_client: RedisClient) -> None:
    repo = RedisOtpRepository(redis_client)
    user_id = _user_id()

    await repo.save_code(user_id, "111111")
    await repo.save_code(user_id, "222222")

    assert await repo.get_active_code_for_user(user_id) == "222222"


async def test_otp_is_scoped_by_user(redis_client: RedisClient) -> None:
    repo = RedisOtpRepository(redis_client)
    await repo.save_code(_user_id(), "123456")

    assert await repo.get_active_code_for_user(_user_id()) is None


async def test_refresh_token_lifecycle(redis_client: RedisClient, raw_redis: Redis) -> None:
    repo = RedisTokenRepository(redis_client)
    user_id = _user_id()

    await repo.save_refresh_token(user_id, "refresh.jwt.token", ttl_seconds=3600)

    assert await repo.get_refresh_token(user_id) == "refresh.jwt.token"
    assert 0 < await raw_redis.ttl(f"refresh:{user_id}") <= 3600

    await repo.delete_refresh_token(user_id)
    assert await repo.get_refresh_token(user_id) is None


async def test_health_assessment_round_trip(redis_client: RedisClient, raw_redis: Redis) -> None:
    repo = RedisHealthRawResponseRepository(redis_client)
    record_id = HealthRecordId(uuid.uuid4())
    assessment = PendingHealthAssessment(
        raw_response={"result": {"is_plant": {"binary": True, "probability": 0.98}}, "suggestions": [1, 2.5, None, "x"]},
        similar_images_urls=("https://img/1.jpg", "https://img/2.jpg"),
    )

    await repo.save(record_id, assessment)

    assert await repo.get(record_id) == assessment
    assert 23 * 3600 < await raw_redis.ttl(f"health_raw:{record_id}") <= 24 * 3600

    await repo.delete(record_id)
    assert await repo.get(record_id) is None


async def test_health_assessment_in_unknown_format_counts_as_expired(redis_client: RedisClient, raw_redis: Redis) -> None:
    repo = RedisHealthRawResponseRepository(redis_client)
    record_id = HealthRecordId(uuid.uuid4())
    await raw_redis.set(f"health_raw:{record_id}", '{"raw": "formato antigo"}')

    assert await repo.get(record_id) is None
