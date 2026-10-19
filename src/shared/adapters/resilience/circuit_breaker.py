import time
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import TypeVar

import structlog

from src.shared.domain.exceptions import ExternalServiceError, ServiceUnavailableError

log = structlog.stdlib.get_logger()

T = TypeVar("T")

_DEFAULT_FAILURE_THRESHOLD = 5
_DEFAULT_RECOVERY_TIMEOUT_SECONDS = 30.0


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


def is_transient_failure(exc: BaseException) -> bool:
    """
    Only transient failures open the circuit: a provider's (ExternalServiceError retryable) or our
    own infrastructure's (ServiceUnavailableError). Invalid image, other 4xx or empty results mean
    the service is answering.
    """
    return isinstance(exc, ServiceUnavailableError) or (isinstance(exc, ExternalServiceError) and exc.retryable)


class CircuitBreaker:
    """
    Circuit Breaker em memória (por processo) para chamadas a APIs externas.
    CLOSED: chamadas passam normalmente e falhas consecutivas são contadas.
    OPEN: chamadas falham imediatamente com ExternalServiceError até o recovery_timeout.
    HALF_OPEN: uma única chamada de teste decide se o circuito fecha ou reabre.
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = _DEFAULT_FAILURE_THRESHOLD,
        recovery_timeout_seconds: float = _DEFAULT_RECOVERY_TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout_seconds
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = 0.0

    @property
    def state(self) -> CircuitState:
        return self._state

    async def call(self, func: Callable[[], Awaitable[T]]) -> T:
        self._before_call()
        try:
            result = await func()
        except Exception as exc:
            if is_transient_failure(exc):
                self._on_failure(exc)
            else:
                self._on_success()
            raise
        except BaseException:
            # Cancelamento durante o teste em HALF_OPEN: libera para um novo teste
            if self._state is CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
            raise
        self._on_success()
        return result

    def _before_call(self) -> None:
        if self._state is CircuitState.CLOSED:
            return

        if self._state is CircuitState.OPEN and self._clock() - self._opened_at >= self._recovery_timeout:
            self._transition(CircuitState.HALF_OPEN)
            return

        raise ExternalServiceError(
            message="Circuit breaker open, try again later.",
            service=self._name,
        )

    def _on_success(self) -> None:
        self._failures = 0
        if self._state is not CircuitState.CLOSED:
            self._transition(CircuitState.CLOSED)

    def _on_failure(self, exc: BaseException) -> None:
        self._failures += 1
        if self._state is CircuitState.HALF_OPEN or self._failures >= self._failure_threshold:
            self._opened_at = self._clock()
            self._transition(CircuitState.OPEN, error=str(exc))

    def _transition(self, state: CircuitState, **extra: object) -> None:
        log.warning(
            "circuit_breaker.state_changed",
            service=self._name,
            from_state=self._state.value,
            to_state=state.value,
            failures=self._failures,
            **extra,
        )
        self._state = state
