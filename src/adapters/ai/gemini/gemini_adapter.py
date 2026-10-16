from src.adapters.ai.gemini.prompt_builder import GeminiPromptBuilder
from src.adapters.ai.gemini.schemas import (
    HealthDiagnosisSchema,
    NutritionalAnalysisSchema,
    SpeciesEnrichmentSchema,
)
from src.domain.ports.plant_enricher import (
    DiseaseAnalysisResult,
    EnrichmentResult,
    HealthDiagnosisEnrichment,
    IPlantEnricher,
    NutritionalEnrichmentResult,
)
from src.shared.adapters import GEMINI_SERVICE, GeminiClient
from src.shared.domain import ExternalServiceError


class GeminiAdapter(IPlantEnricher):
    def __init__(self, api_key: str) -> None:
        self._client = GeminiClient(api_key)
        self._builder = GeminiPromptBuilder()

    async def enrich_species(self, scientific_name: str) -> EnrichmentResult:
        parsed = await self._client.generate(
            self._builder.enrich_species(scientific_name), SpeciesEnrichmentSchema
        )
        return EnrichmentResult(
            scientific_name=scientific_name,
            source="gemini",
            is_edible=parsed.is_edible,
            water_frequency_per_week=parsed.water_frequency_per_week,
            light_requirement=parsed.light_requirement,
            soil_type=parsed.soil_type,
            best_planting_season=parsed.best_planting_season,
            origin_country=parsed.origin_country,
            habitat=parsed.habitat,
            popular_names=tuple(parsed.common_names),
        )

    async def enrich_nutritional(self, scientific_name: str) -> NutritionalEnrichmentResult:
        parsed = await self._client.generate(
            self._builder.nutritional_analysis(scientific_name), NutritionalAnalysisSchema
        )
        return NutritionalEnrichmentResult(
            scientific_name=scientific_name,
            source="gemini",
            tea_preparation=parsed.tea_preparation,
            tea_benefits=parsed.tea_benefits,
            food_recipe_name=parsed.food_recipe_name,
            food_recipe_ingredients=tuple(parsed.food_recipe_ingredients),
            medicinal_uses=parsed.medicinal_uses,
            seasoning_pairings=parsed.seasoning_pairings,
        )

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
