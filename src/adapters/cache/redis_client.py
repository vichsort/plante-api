"""
Fachada tipada sobre o cliente assíncrono do redis-py.

O redis-py tipa o retorno de todo comando como `Any`; aqui ficam só os comandos que o projeto
usa, com o tipo de retorno conferido em execução. É o único ponto do código que toca o
redis-py: o resto (repositórios de cache, rate limit, readiness) depende desta classe.
Falhas de conexão viram `ExternalServiceError(retryable=True)`.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.domain.exceptions import ExternalServiceError

_SERVICE = "Redis"


@asynccontextmanager
async def _translated_errors() -> AsyncIterator[None]:
    try:
        yield
    except (RedisError, OSError) as exc:
        raise ExternalServiceError(
            message=f"{type(exc).__name__}: {exc}", service=_SERVICE, retryable=True
        ) from exc


class RedisClient:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @classmethod
    def from_url(cls, url: str, socket_timeout: float, socket_connect_timeout: float) -> "RedisClient":
        return cls(Redis.from_url(
            url,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
        ))

    async def get(self, key: str) -> bytes | None:
        async with _translated_errors():
            value = await self._redis.get(key)
        if value is None or isinstance(value, bytes):
            return value
        raise TypeError(f"Unexpected Redis GET reply: {type(value).__name__}")

    async def set(self, key: str, value: str | bytes, ttl_seconds: int) -> None:
        async with _translated_errors():
            await self._redis.set(key, value, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        async with _translated_errors():
            await self._redis.delete(key)

    async def increment_with_expiry(self, key: str, ttl_seconds: int) -> int:
        """INCR + EXPIRE na mesma transação; devolve o valor após o incremento."""
        async with _translated_errors(), self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, ttl_seconds)
            count, _ = await pipe.execute()
        if isinstance(count, int):
            return count
        raise TypeError(f"Unexpected Redis INCR reply: {type(count).__name__}")

    async def ping(self) -> None:
        async with _translated_errors():
            await self._redis.ping()

    async def close(self) -> None:
        await self._redis.aclose()
