from src.modules.identification.adapters.resilience.circuit_breaker import (
    CircuitBreakerPlantIdentifier,
)
from src.modules.identification.tests.fakes import StubPlantIdentifier
from src.shared.adapters import CircuitBreaker


async def test_identifier_is_called_through_the_breaker() -> None:
    # Arrange
    inner = StubPlantIdentifier()
    wrapper = CircuitBreakerPlantIdentifier(inner, CircuitBreaker("PlantNet"))

    # Act
    result = await wrapper.identify(b"img", latitude=1.0, longitude=2.0)

    # Assert
    assert result == inner.result
    assert inner.calls == [(b"img", 1.0, 2.0)]
