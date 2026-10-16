from src.modules.catalog.adapters.gemini.prompts import SpeciesPrompts
from src.modules.catalog.adapters.gemini.schemas import (
    NutritionalAnalysisSchema,
    SpeciesEnrichmentSchema,
)
from src.modules.catalog.domain.ports.species_enricher import (
    EnrichmentResult,
    ISpeciesEnricher,
    NutritionalEnrichmentResult,
)
from src.shared.adapters import GeminiClient


class GeminiSpeciesEnricher(ISpeciesEnricher):
    def __init__(self, api_key: str) -> None:
        self._client = GeminiClient(api_key)
        self._prompts = SpeciesPrompts()

    async def enrich_species(self, scientific_name: str) -> EnrichmentResult:
        parsed = await self._client.generate(
            self._prompts.enrich_species(scientific_name), SpeciesEnrichmentSchema
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
            self._prompts.nutritional_analysis(scientific_name), NutritionalAnalysisSchema
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
