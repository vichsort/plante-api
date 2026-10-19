from src.modules.identification.domain.ports.plant_identifier import (
    IdentificationResult,
    IPlantIdentifier,
)
from src.shared.adapters import CircuitBreaker


class CircuitBreakerPlantIdentifier(IPlantIdentifier):
    """Decorator que protege um IPlantIdentifier com Circuit Breaker."""
    def __init__(self, inner: IPlantIdentifier, breaker: CircuitBreaker) -> None:
        self._inner = inner
        self._breaker = breaker

    async def identify(
        self,
        image_bytes: bytes,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> IdentificationResult:
        return await self._breaker.call(
            lambda: self._inner.identify(image_bytes, latitude=latitude, longitude=longitude)
        )
