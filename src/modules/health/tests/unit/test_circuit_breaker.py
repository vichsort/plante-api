import pytest

from src.modules.health.adapters.resilience.circuit_breaker import (
    CircuitBreakerHealthAnalyzer,
)
from src.modules.health.tests.fakes import StubHealthAnalyzer
from src.shared.adapters import CircuitBreaker
from src.shared.domain import ExternalServiceError


async def test_analyzer_is_called_through_the_breaker() -> None:
    # Arrange
    inner = StubHealthAnalyzer()
    wrapper = CircuitBreakerHealthAnalyzer(inner, CircuitBreaker("Kindwise"))

    # Act
    result = await wrapper.assess_health(b"img")

    # Assert
    assert result == inner.result
    assert inner.received == [b"img"]


async def test_open_breaker_refuses_without_calling_the_provider() -> None:
    # Arrange: o breaker é o mesmo da identificação; falhas lá abrem a saúde também
    breaker = CircuitBreaker("Kindwise", failure_threshold=1)
    inner = StubHealthAnalyzer()

    async def failing() -> None:
        raise ExternalServiceError(service="Kindwise", retryable=True)

    with pytest.raises(ExternalServiceError):
        await breaker.call(failing)

    # Act & Assert
    with pytest.raises(ExternalServiceError):
        await CircuitBreakerHealthAnalyzer(inner, breaker).assess_health(b"img")
    assert inner.received == []
