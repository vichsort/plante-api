from src.adapters.ai.gemini.prompt_builder import GeminiPromptBuilder
from src.adapters.ai.gemini.schemas import HealthDiagnosisSchema
from src.domain.ports.health_enricher import (
    DiseaseAnalysisResult,
    HealthDiagnosisEnrichment,
    IHealthEnricher,
)
from src.shared.adapters import GEMINI_SERVICE, GeminiClient
from src.shared.domain import ExternalServiceError


class GeminiHealthEnricher(IHealthEnricher):
    """Complemento do Gemini ao diagnóstico. O enriquecimento de espécie é do catalog."""

    def __init__(self, api_key: str) -> None:
        self._client = GeminiClient(api_key)
        self._builder = GeminiPromptBuilder()

    async def analyze_disease(self, scientific_name: str, disease_name: str) -> DiseaseAnalysisResult:
        parsed = await self._diagnose(scientific_name, [disease_name])
        return DiseaseAnalysisResult(
            scientific_name=scientific_name,
            disease_name=disease_name,
            source="gemini",
            symptoms=tuple(parsed.issues_detected),
            treatment_steps=tuple(parsed.treatment_plan),
            recovery_estimate_days=parsed.recovery_estimate_days,
        )

    async def diagnose_health(self, scientific_name: str, issues: list[str]) -> HealthDiagnosisEnrichment:
        parsed = await self._diagnose(scientific_name, issues)
        return HealthDiagnosisEnrichment(
            vitality_score=parsed.vitality_score,
            treatment_plan=tuple(parsed.treatment_plan),
            recovery_estimate_days=parsed.recovery_estimate_days,
            notes=parsed.notes,
        )

    async def _diagnose(self, scientific_name: str, issues: list[str]) -> HealthDiagnosisSchema:
        parsed = await self._client.generate(
            self._builder.health_diagnosis(scientific_name, issues), HealthDiagnosisSchema
        )
        if not 0.0 <= parsed.vitality_score <= 1.0:
            raise ExternalServiceError(
                message=f"vitality_score out of range: {parsed.vitality_score}.", service=GEMINI_SERVICE
            )
        return parsed
