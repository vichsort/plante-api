from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class DiseaseHint:
    name: str
    probability: float
    similar_images_urls: tuple[str, ...]  # URLs brutas do Kindwise

@dataclass(frozen=True)
class HealthAssessmentResult:
    is_healthy: bool
    health_probability: float           # 0.0 a 1.0 — score bruto do Kindwise
    diseases: tuple[DiseaseHint, ...]
    raw_response: dict                  # JSON bruto preservado integralmente

    @property
    def all_similar_images_urls(self) -> tuple[str, ...]:
        """Agrega todas as similar_images_urls de todas as doenças detectadas."""
        urls = []
        for disease in self.diseases:
            urls.extend(disease.similar_images_urls)
        return tuple(urls)


class IHealthAnalyzer(ABC):
    @abstractmethod
    async def assess_health(self, image_b64: str) -> HealthAssessmentResult:
        """Avalia saúde da planta via imagem. Retorna score + doenças detectadas."""
        ...