from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class DiseaseAnalysisResult:
    scientific_name: str
    disease_name: str
    source: str
    symptoms: tuple[str, ...] = ()
    treatment_steps: tuple[str, ...] = ()
    recovery_estimate_days: int | None = None

@dataclass(frozen=True)
class HealthDiagnosisEnrichment:
    """Análise complementar do Gemini para uma planta com problemas de saúde."""
    vitality_score: float
    treatment_plan: tuple[str, ...] = ()
    recovery_estimate_days: int | None = None
    notes: str | None = None


class IHealthEnricher(ABC):
    """Complemento do Gemini ao diagnóstico (o enriquecimento de espécie é do catalog)."""

    @abstractmethod
    async def analyze_disease(
        self, scientific_name: str, disease_name: str
    ) -> DiseaseAnalysisResult:
        """Analisa uma doença específica diagnosticada numa planta."""
        ...

    @abstractmethod
    async def diagnose_health(
        self, scientific_name: str, issues: list[str]
    ) -> HealthDiagnosisEnrichment:
        """Enriquece o diagnóstico de saúde de uma planta."""
        ...
