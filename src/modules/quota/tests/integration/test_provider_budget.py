"""The service's daily limit over the real Redis: one count per local day, shared, and it expires."""
from datetime import UTC, datetime, timedelta

import pytest
from redis.asyncio import Redis

from src.modules.quota.adapters.redis.usage_counter import RedisUsageCounter
from src.modules.quota.domain.exceptions import ServiceDailyLimitError
from src.modules.quota.domain.services.provider_budget import ProviderBudget
from src.shared.adapters import RedisClient
from src.shared.domain import LocalCalendar

# 23:30 in São Paulo: still the 16th locally, already the 17th in UTC
LATE_EVENING = datetime(2026, 10, 17, 2, 30, tzinfo=UTC)
CALENDAR = LocalCalendar.from_name("America/Sao_Paulo")


def _budget(redis_client: RedisClient, daily_limit: int) -> ProviderBudget:
    return ProviderBudget(RedisUsageCounter(redis_client, "provider_calls"), CALENDAR, daily_limit)


async def test_the_limit_holds_across_budgets_and_renews_the_next_local_day(redis_client: RedisClient) -> None:
    # Arrange: two API processes share the count
    first, second = _budget(redis_client, 2), _budget(redis_client, 2)

    # Act
    await first.take(LATE_EVENING)
    await second.take(LATE_EVENING)

    # Assert
    with pytest.raises(ServiceDailyLimitError):
        await first.take(LATE_EVENING + timedelta(minutes=10))  # still the 16th locally
    await second.take(LATE_EVENING + timedelta(hours=1))  # the 17th: a new day


async def test_the_day_key_expires_on_its_own(redis_client: RedisClient, raw_redis: Redis) -> None:
    # Act
    await _budget(redis_client, 5).take(LATE_EVENING)

    # Assert
    ttl = await raw_redis.ttl("plante:usage:provider_calls:2026-10-16")
    assert 24 * 60 * 60 < ttl <= 2 * 24 * 60 * 60
