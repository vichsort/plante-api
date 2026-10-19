"""Contrato do `RedisClient` contra um Redis real: o fake do rate limit assume este comportamento."""
import socket

import pytest
from redis.asyncio import Redis
from structlog.testing import capture_logs

from src.shared.adapters import RedisClient
from src.shared.domain import InternalError, ServiceUnavailableError


async def test_get_missing_key_returns_none(redis_client: RedisClient) -> None:
    # Act
    value = await redis_client.get("missing")

    # Assert
    assert value is None


async def test_set_stores_value_as_bytes_with_ttl(redis_client: RedisClient, raw_redis: Redis) -> None:
    # Act
    await redis_client.set("text", "olá", ttl_seconds=60)
    await redis_client.set("binary", b"\x00\xff", ttl_seconds=60)

    # Assert
    assert await redis_client.get("text") == "olá".encode()
    assert await redis_client.get("binary") == b"\x00\xff"
    assert 0 < await raw_redis.ttl("text") <= 60


async def test_set_overwrites_value_and_ttl(redis_client: RedisClient, raw_redis: Redis) -> None:
    # Arrange
    await redis_client.set("key", "first", ttl_seconds=600)

    # Act
    await redis_client.set("key", "second", ttl_seconds=30)

    # Assert
    assert await redis_client.get("key") == b"second"
    assert await raw_redis.ttl("key") <= 30


async def test_delete_removes_key_and_ignores_missing(redis_client: RedisClient) -> None:
    # Arrange
    await redis_client.set("key", "value", ttl_seconds=60)

    # Act
    await redis_client.delete("key")
    await redis_client.delete("key")

    # Assert
    assert await redis_client.get("key") is None


async def test_increment_with_expiry_counts_and_sets_ttl(redis_client: RedisClient, raw_redis: Redis) -> None:
    # Act
    first = await redis_client.increment_with_expiry("counter", ttl_seconds=60)
    second = await redis_client.increment_with_expiry("counter", ttl_seconds=60)

    # Assert
    assert (first, second) == (1, 2)
    assert 0 < await raw_redis.ttl("counter") <= 60


async def test_increment_with_expiry_restarts_after_key_expires(redis_client: RedisClient, raw_redis: Redis) -> None:
    # Arrange
    await redis_client.increment_with_expiry("counter", ttl_seconds=60)
    await raw_redis.delete("counter")  # equivale à janela do rate limit ter expirado

    # Act
    count = await redis_client.increment_with_expiry("counter", ttl_seconds=60)

    # Assert
    assert count == 1


async def test_rejected_command_is_an_internal_error(redis_client: RedisClient, raw_redis: Redis) -> None:
    # Arrange
    await raw_redis.rpush("list", "a")

    # Act & Assert: WRONGTYPE is our bug; the detail goes to the log, not to the client
    with capture_logs() as logs, pytest.raises(InternalError) as exc_info:
        await redis_client.get("list")
    assert "WRONGTYPE" not in exc_info.value.message
    assert any(entry["event"] == "redis.command_rejected" and "WRONGTYPE" in entry["error"] for entry in logs)


async def test_ping(redis_client: RedisClient) -> None:
    # Act & Assert: não levanta
    await redis_client.ping()


def _unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
        return port


async def test_unreachable_redis_is_a_service_unavailable() -> None:
    # Arrange
    client = RedisClient.from_url(f"redis://127.0.0.1:{_unused_port()}/0", socket_timeout=0.5, socket_connect_timeout=0.5)
    try:
        # Act & Assert
        with pytest.raises(ServiceUnavailableError):
            await client.ping()
    finally:
        await client.close()
