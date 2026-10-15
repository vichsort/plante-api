"""Contrato do `RedisClient` contra um Redis real: o fake do rate limit assume este comportamento."""
import socket

import pytest
from redis.asyncio import Redis

from src.adapters.cache.redis_client import RedisClient
from src.domain.exceptions import ExternalServiceError


async def test_get_missing_key_returns_none(redis_client: RedisClient) -> None:
    assert await redis_client.get("missing") is None


async def test_set_stores_value_as_bytes_with_ttl(redis_client: RedisClient, raw_redis: Redis) -> None:
    await redis_client.set("text", "olá", ttl_seconds=60)
    await redis_client.set("binary", b"\x00\xff", ttl_seconds=60)

    assert await redis_client.get("text") == "olá".encode()
    assert await redis_client.get("binary") == b"\x00\xff"
    assert 0 < await raw_redis.ttl("text") <= 60


async def test_set_overwrites_value_and_ttl(redis_client: RedisClient, raw_redis: Redis) -> None:
    await redis_client.set("key", "first", ttl_seconds=600)
    await redis_client.set("key", "second", ttl_seconds=30)

    assert await redis_client.get("key") == b"second"
    assert await raw_redis.ttl("key") <= 30


async def test_delete_removes_key_and_ignores_missing(redis_client: RedisClient) -> None:
    await redis_client.set("key", "value", ttl_seconds=60)

    await redis_client.delete("key")
    await redis_client.delete("key")

    assert await redis_client.get("key") is None


async def test_increment_with_expiry_counts_and_sets_ttl(redis_client: RedisClient, raw_redis: Redis) -> None:
    assert await redis_client.increment_with_expiry("counter", ttl_seconds=60) == 1
    assert await redis_client.increment_with_expiry("counter", ttl_seconds=60) == 2
    assert 0 < await raw_redis.ttl("counter") <= 60


async def test_increment_with_expiry_restarts_after_key_expires(redis_client: RedisClient, raw_redis: Redis) -> None:
    await redis_client.increment_with_expiry("counter", ttl_seconds=60)
    await raw_redis.delete("counter")  # equivale à janela do rate limit ter expirado

    assert await redis_client.increment_with_expiry("counter", ttl_seconds=60) == 1


async def test_wrong_type_reply_is_translated(redis_client: RedisClient, raw_redis: Redis) -> None:
    await raw_redis.rpush("list", "a")

    # WRONGTYPE vem do servidor como erro do redis-py, traduzido como os demais
    with pytest.raises(ExternalServiceError):
        await redis_client.get("list")


async def test_ping(redis_client: RedisClient) -> None:
    await redis_client.ping()


def _unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port: int = sock.getsockname()[1]
        return port


async def test_unreachable_redis_raises_retryable_external_error() -> None:
    client = RedisClient.from_url(f"redis://127.0.0.1:{_unused_port()}/0", socket_timeout=0.5, socket_connect_timeout=0.5)
    try:
        with pytest.raises(ExternalServiceError) as exc_info:
            await client.ping()
        assert exc_info.value.retryable is True
    finally:
        await client.close()
