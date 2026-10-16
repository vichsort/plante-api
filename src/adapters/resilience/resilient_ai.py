from src.domain.ports.health_analyzer import HealthAssessmentResult, IHealthAnalyzer
from src.domain.ports.plant_identifier import IdentificationResult, IPlantIdentifier
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


class CircuitBreakerHealthAnalyzer(IHealthAnalyzer):
    """Decorator que protege um IHealthAnalyzer com Circuit Breaker."""
    def __init__(self, inner: IHealthAnalyzer, breaker: CircuitBreaker) -> None:
        self._inner = inner
        self._breaker = breaker

    async def assess_health(self, image_bytes: bytes) -> HealthAssessmentResult:
        return await self._breaker.call(lambda: self._inner.assess_health(image_bytes))
