from src.modules.health.domain.ports.health_analyzer import (
    HealthAssessmentResult,
    IHealthAnalyzer,
)
from src.shared.adapters import CircuitBreaker


class CircuitBreakerHealthAnalyzer(IHealthAnalyzer):
    """Decorator que protege um IHealthAnalyzer com Circuit Breaker."""
    def __init__(self, inner: IHealthAnalyzer, breaker: CircuitBreaker) -> None:
        self._inner = inner
        self._breaker = breaker

    async def assess_health(self, image_bytes: bytes) -> HealthAssessmentResult:
        return await self._breaker.call(lambda: self._inner.assess_health(image_bytes))
