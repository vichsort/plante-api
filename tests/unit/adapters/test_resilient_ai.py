from src.adapters.resilience import CircuitBreakerPlantIdentifier
from src.shared.adapters import CircuitBreaker


async def test_plant_identifier_wrapper_delegates_through_breaker():
    class _Identifier:
        async def identify(self, image_bytes, latitude=None, longitude=None):
            return (image_bytes, latitude, longitude)

    wrapper = CircuitBreakerPlantIdentifier(_Identifier(), CircuitBreaker("PlantNet"))
    assert await wrapper.identify(b"img", latitude=1.0, longitude=2.0) == (b"img", 1.0, 2.0)
