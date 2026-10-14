import asyncio

import httpx
import pytest

from src.adapters.resilience import (
    CircuitBreaker,
    CircuitBreakerPlantIdentifier,
    CircuitState,
)
from src.domain.exceptions import ExternalServiceError


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _status_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://provider.test")
    return httpx.HTTPStatusError("error", request=request, response=httpx.Response(status, request=request))


async def _fail(exc: BaseException):
    raise exc


async def _ok():
    return "ok"


async def _trip(breaker: CircuitBreaker, times: int) -> None:
    for _ in range(times):
        with pytest.raises(httpx.ConnectError):
            await breaker.call(lambda: _fail(httpx.ConnectError("down")))


@pytest.mark.asyncio
async def test_opens_after_threshold_and_fails_fast():
    breaker = CircuitBreaker("Kindwise", failure_threshold=2, clock=_Clock())
    await _trip(breaker, 2)
    assert breaker.state is CircuitState.OPEN

    called = False

    async def should_not_run():
        nonlocal called
        called = True

    with pytest.raises(ExternalServiceError):
        await breaker.call(should_not_run)
    assert called is False


@pytest.mark.asyncio
async def test_half_open_success_closes_circuit():
    clock = _Clock()
    breaker = CircuitBreaker("Kindwise", failure_threshold=1, recovery_timeout_seconds=30, clock=clock)
    await _trip(breaker, 1)

    clock.now = 30
    assert await breaker.call(_ok) == "ok"
    assert breaker.state is CircuitState.CLOSED


@pytest.mark.asyncio
async def test_half_open_failure_reopens_circuit():
    clock = _Clock()
    breaker = CircuitBreaker("Kindwise", failure_threshold=1, recovery_timeout_seconds=30, clock=clock)
    await _trip(breaker, 1)

    clock.now = 30
    await _trip(breaker, 1)
    assert breaker.state is CircuitState.OPEN
    with pytest.raises(ExternalServiceError):
        await breaker.call(_ok)


@pytest.mark.asyncio
async def test_half_open_allows_single_probe():
    clock = _Clock()
    breaker = CircuitBreaker("Kindwise", failure_threshold=1, recovery_timeout_seconds=30, clock=clock)
    await _trip(breaker, 1)
    clock.now = 30

    release = asyncio.Event()

    async def slow_probe():
        await release.wait()
        return "ok"

    probe = asyncio.create_task(breaker.call(slow_probe))
    await asyncio.sleep(0)
    with pytest.raises(ExternalServiceError):
        await breaker.call(_ok)

    release.set()
    assert await probe == "ok"
    assert breaker.state is CircuitState.CLOSED


@pytest.mark.asyncio
async def test_cancelled_probe_allows_new_probe():
    clock = _Clock()
    breaker = CircuitBreaker("Kindwise", failure_threshold=1, recovery_timeout_seconds=30, clock=clock)
    await _trip(breaker, 1)
    clock.now = 30

    probe = asyncio.create_task(breaker.call(asyncio.Event().wait))
    await asyncio.sleep(0)
    probe.cancel()
    with pytest.raises(asyncio.CancelledError):
        await probe

    assert await breaker.call(_ok) == "ok"


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [_status_error(400), _status_error(404), ValueError("no suggestions")])
async def test_client_errors_do_not_count_as_failures(exc):
    breaker = CircuitBreaker("Kindwise", failure_threshold=1, clock=_Clock())
    with pytest.raises(type(exc)):
        await breaker.call(lambda: _fail(exc))
    assert breaker.state is CircuitState.CLOSED


@pytest.mark.asyncio
@pytest.mark.parametrize("exc", [_status_error(500), _status_error(429), httpx.ReadTimeout("slow"), TimeoutError()])
async def test_provider_errors_count_as_failures(exc):
    breaker = CircuitBreaker("Kindwise", failure_threshold=1, clock=_Clock())
    with pytest.raises(type(exc)):
        await breaker.call(lambda: _fail(exc))
    assert breaker.state is CircuitState.OPEN


@pytest.mark.asyncio
async def test_plant_identifier_wrapper_delegates_through_breaker():
    class _Identifier:
        async def identify(self, image_bytes, latitude=None, longitude=None):
            return (image_bytes, latitude, longitude)

    wrapper = CircuitBreakerPlantIdentifier(_Identifier(), CircuitBreaker("PlantNet"))
    assert await wrapper.identify(b"img", latitude=1.0, longitude=2.0) == (b"img", 1.0, 2.0)
