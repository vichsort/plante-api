import asyncio
from collections.abc import Awaitable, Callable

import pytest

from src.shared.adapters import CircuitBreaker, CircuitState
from src.shared.domain import (
    ExternalServiceError,
    InternalError,
    InvalidImageError,
    PlantEError,
    ServiceUnavailableError,
)


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _provider_down() -> ExternalServiceError:
    return ExternalServiceError(service="Kindwise", retryable=True)


def _failing(exc: BaseException) -> Callable[[], Awaitable[str]]:
    async def call() -> str:
        raise exc
    return call


async def _ok() -> str:
    return "ok"


async def _trip(breaker: CircuitBreaker, times: int) -> None:
    for _ in range(times):
        with pytest.raises(ExternalServiceError):
            await breaker.call(_failing(_provider_down()))


async def test_opens_after_threshold_and_fails_fast() -> None:
    # Arrange
    breaker = CircuitBreaker("Kindwise", failure_threshold=2, clock=_Clock())
    called = False

    async def should_not_run() -> None:
        nonlocal called
        called = True

    # Act
    await _trip(breaker, 2)

    # Assert
    assert breaker.state is CircuitState.OPEN
    with pytest.raises(ExternalServiceError):
        await breaker.call(should_not_run)
    assert called is False


async def test_half_open_success_closes_circuit() -> None:
    # Arrange
    clock = _Clock()
    breaker = CircuitBreaker("Kindwise", failure_threshold=1, recovery_timeout_seconds=30, clock=clock)
    await _trip(breaker, 1)
    clock.now = 30

    # Act
    result = await breaker.call(_ok)

    # Assert
    assert result == "ok"
    assert breaker.state is CircuitState.CLOSED


async def test_half_open_failure_reopens_circuit() -> None:
    # Arrange
    clock = _Clock()
    breaker = CircuitBreaker("Kindwise", failure_threshold=1, recovery_timeout_seconds=30, clock=clock)
    await _trip(breaker, 1)
    clock.now = 30

    # Act
    await _trip(breaker, 1)

    # Assert
    assert breaker.state is CircuitState.OPEN
    with pytest.raises(ExternalServiceError):
        await breaker.call(_ok)


async def test_half_open_allows_single_probe() -> None:
    # Arrange
    clock = _Clock()
    breaker = CircuitBreaker("Kindwise", failure_threshold=1, recovery_timeout_seconds=30, clock=clock)
    await _trip(breaker, 1)
    clock.now = 30
    release = asyncio.Event()

    async def slow_probe() -> str:
        await release.wait()
        return "ok"

    # Act
    probe = asyncio.create_task(breaker.call(slow_probe))
    await asyncio.sleep(0)

    # Assert: enquanto a sonda roda, as outras chamadas falham rápido
    with pytest.raises(ExternalServiceError):
        await breaker.call(_ok)
    release.set()
    assert await probe == "ok"
    assert breaker.state is CircuitState.CLOSED


async def test_cancelled_probe_allows_new_probe() -> None:
    # Arrange
    clock = _Clock()
    breaker = CircuitBreaker("Kindwise", failure_threshold=1, recovery_timeout_seconds=30, clock=clock)
    await _trip(breaker, 1)
    clock.now = 30
    probe = asyncio.create_task(breaker.call(asyncio.Event().wait))
    await asyncio.sleep(0)

    # Act
    probe.cancel()
    with pytest.raises(asyncio.CancelledError):
        await probe

    # Assert
    assert await breaker.call(_ok) == "ok"


@pytest.mark.parametrize(
    "exc",
    [
        InvalidImageError(),
        ExternalServiceError(service="Kindwise"),
        InternalError(),  # e.g. a command Redis refused: the server is answering
        ValueError("no suggestions"),
        TimeoutError(),
    ],
)
async def test_non_retryable_errors_do_not_count_as_failures(exc: Exception) -> None:
    # Arrange
    breaker = CircuitBreaker("Kindwise", failure_threshold=1, clock=_Clock())

    # Act
    with pytest.raises(type(exc)):
        await breaker.call(_failing(exc))

    # Assert
    assert breaker.state is CircuitState.CLOSED


@pytest.mark.parametrize("exc", [_provider_down(), ServiceUnavailableError()])
async def test_transient_failures_count_as_failures(exc: PlantEError) -> None:
    # Arrange: a provider's retryable failure or our own infrastructure (Redis) down
    breaker = CircuitBreaker("Kindwise", failure_threshold=1, clock=_Clock())

    # Act
    with pytest.raises(type(exc)):
        await breaker.call(_failing(exc))

    # Assert
    assert breaker.state is CircuitState.OPEN
