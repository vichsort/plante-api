from collections.abc import Iterator
from typing import Any

import pytest
import structlog
from celery import Celery
from celery.contrib.testing.worker import start_worker

import src.infrastructure.celery_config  # noqa: F401  (registra os sinais de correlation ID)

app = Celery("correlation-test", broker="memory://", backend="cache+memory://")
app.conf.broker_transport_options = {"polling_interval": 0.01}


@app.task(name="test.capture_correlation_id")
def capture_correlation_id() -> Any:
    return structlog.contextvars.get_contextvars().get("correlation_id")


@pytest.fixture(scope="module")
def worker() -> Iterator[None]:
    with start_worker(app, perform_ping_check=False, pool="solo"):
        yield


@pytest.fixture(autouse=True)
def clean_context() -> Iterator[None]:
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


def test_task_inherits_correlation_id_from_publisher(worker: None) -> None:
    structlog.contextvars.bind_contextvars(correlation_id="req-123")
    assert capture_correlation_id.delay().get(timeout=10, interval=0.01) == "req-123"


def test_task_without_origin_gets_its_own_id(worker: None) -> None:
    first = capture_correlation_id.delay().get(timeout=10, interval=0.01)
    second = capture_correlation_id.delay().get(timeout=10, interval=0.01)
    assert first and second and first != second
