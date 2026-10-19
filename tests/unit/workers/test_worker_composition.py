"""O worker real: tasks seguidas, cada uma no próprio event loop, com o container ligado pela composição."""
import asyncio
import gc
from collections.abc import Iterator
from uuid import uuid4

import pytest
from dependency_injector import providers
from redis.asyncio import Redis

from src.bootstrap import worker
from src.bootstrap.settings import Settings
from src.modules.identity.tests.fakes import RecordingEmailSender
from src.modules.identity.workers import send_verification_email_task


@pytest.fixture
def worker_on_test_redis(redis_url: str) -> Iterator[RecordingEmailSender]:
    host, port = redis_url.removeprefix("redis://").removesuffix("/0").split(":")
    sender = RecordingEmailSender()
    container = worker.container
    with (
        container.settings.override(providers.Object(Settings(redis_endpoint=host, redis_port=int(port), redis_password=""))),
        container.identity.email_sender.override(providers.Object(sender)),
    ):
        container.reset_singletons()
        worker.wire(container)
        yield sender
    container.reset_singletons()


async def _codes(redis_url: str, user_ids: list[str]) -> list[bytes | None]:
    redis = Redis.from_url(redis_url)
    try:
        return [await redis.get(f"otp:{user_id}") for user_id in user_ids]
    finally:
        await redis.aclose()


# Um cliente fechado só pelo coletor de lixo, com o loop dele já fechado, gera "Event loop is closed"
@pytest.mark.filterwarnings("error::pytest.PytestUnraisableExceptionWarning")
def test_consecutive_tasks_each_get_a_fresh_redis_client(worker_on_test_redis: RecordingEmailSender, redis_url: str) -> None:
    # Arrange: `apply` roda a task aqui, com os sinais do Celery; cada chamada abre um event loop novo
    user_ids = [str(uuid4()), str(uuid4())]

    # Act: sem recriar os singletons, a segunda usaria o cliente do Redis do loop já fechado
    for user_id in user_ids:
        send_verification_email_task.apply(kwargs={"user_id": user_id, "email": "worker@plante.org"}, throw=True)
    gc.collect()  # antes, o coletor fechava aqui os clientes das tasks terminadas

    # Assert
    codes = asyncio.run(_codes(redis_url, user_ids))
    assert all(codes)
    assert [code for _, code in worker_on_test_redis.sent] == [code.decode() for code in codes if code]
