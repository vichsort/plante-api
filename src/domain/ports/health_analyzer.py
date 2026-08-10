from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class DiseaseHint:
    name: str
    probability: float
    similar_images_urls: tuple[str, ...]

@dataclass(frozen=True)
class HealthAssessmentResult:
    is_healthy: bool
    health_probability: float
    diseases: tuple[DiseaseHint, ...]
    raw_response: dict

    @property
    def all_similar_images_urls(self) -> tuple[str, ...]:
        urls: list[str] = []
        for disease in self.diseases:
            urls.extend(disease.similar_images_urls)
        return tuple(urls)


class IHealthAnalyzer(ABC):
    @abstractmethod
    async def assess_health(self, image_bytes: bytes) -> HealthAssessmentResult:
        ...