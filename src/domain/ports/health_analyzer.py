from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class DiseaseHint:
    name: str
    probability: float

@dataclass(frozen=True)
class HealthAssessmentResult:
    is_healthy: bool
    health_probability: float          # 0.0 a 1.0 — score bruto do Kindwise
    diseases: tuple[DiseaseHint, ...]


class IHealthAnalyzer(ABC):
    @abstractmethod
    async def assess_health(self, image_b64: str) -> HealthAssessmentResult:
        """Avalia saúde da planta via imagem. Retorna score + doenças detectadas."""
        ...