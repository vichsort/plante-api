import asyncio
import json
from typing import Any

from google import genai
from google.genai import errors as genai_errors

from src.adapters.ai.gemini.prompt_builder import GeminiPromptBuilder
from src.adapters.ai.gemini.response_parser import GeminiResponseParser
from src.adapters.ai.provider_errors import (
    provider_status_error,
    translate_provider_errors,
)
from src.domain.exceptions import ExternalServiceError
from src.domain.ports.plant_enricher import (
    DiseaseAnalysisResult,
    EnrichmentResult,
    IPlantEnricher,
    NutritionalEnrichmentResult,
)

_MODEL = "gemini-2.5-flash"
_SERVICE = "Gemini"

class GeminiAdapter(IPlantEnricher):
    _client: genai.Client
    _builder: GeminiPromptBuilder
    _parser: GeminiResponseParser

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._builder = GeminiPromptBuilder()
        self._parser = GeminiResponseParser()

    async def enrich_species(self, scientific_name: str) -> EnrichmentResult:
        prompt = self._builder.enrich_species(scientific_name)
        raw = await self._generate(prompt)
        parsed = self._parser.parse_enrich_species(raw)
        return EnrichmentResult(
            scientific_name=scientific_name,
            source="gemini",
            is_edible=parsed.get("is_edible"),
            water_frequency_per_week=parsed.get("water_frequency_per_week"),
            light_requirement=parsed.get("light_requirement"),
            soil_type=parsed.get("soil_type"),
            best_planting_season=parsed.get("best_planting_season"),
            origin_country=parsed.get("origin_country"),
            habitat=parsed.get("habitat"),
            popular_names=tuple(parsed.get("popular_names") or []),
            description=parsed.get("description"),
        )

    async def enrich_nutritional(self, scientific_name: str) -> NutritionalEnrichmentResult:
        prompt = self._builder.nutritional_analysis(scientific_name)
        raw = await self._generate(prompt)
        parsed = self._parser.parse_nutritional(raw)
        return NutritionalEnrichmentResult(
            scientific_name=scientific_name,
            source="gemini",
            tea_preparation=parsed.get("tea_preparation"),
            tea_benefits=parsed.get("tea_benefits"),
            food_recipe_name=parsed.get("food_recipe_name"),
            food_recipe_ingredients=tuple(parsed.get("food_recipe_ingredients") or []),
            medicinal_uses=parsed.get("medicinal_uses"),
            seasoning_pairings=parsed.get("seasoning_pairings"),
        )

    async def analyze_disease(self, scientific_name: str, disease_name: str) -> DiseaseAnalysisResult:
        prompt = self._builder.health_diagnosis(scientific_name, [disease_name])
        raw = await self._generate(prompt)
        parsed = self._parser.parse_health_diagnosis(raw)
        return DiseaseAnalysisResult(
            scientific_name=scientific_name,
            disease_name=disease_name,
            source="gemini",
            symptoms=tuple(parsed.get("issues_detected") or []),
            treatment_steps=tuple(parsed.get("treatment_plan") or []),
            recovery_estimate_days=parsed.get("recovery_estimate_days"),
        )

    async def diagnose_health(self, scientific_name: str, issues: list[str]) -> dict[str, Any]:
        prompt = self._builder.health_diagnosis(scientific_name, issues)
        raw = await self._generate(prompt)
        return self._parser.parse_health_diagnosis(raw)

    async def _generate(self, prompt: str) -> dict[str, Any]:
        try:
            # Gemini não recebe imagem: nenhum status do provedor significa imagem inválida
            async with translate_provider_errors(_SERVICE, invalid_image_statuses=frozenset()):
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._client.models.generate_content(
                        model=_MODEL,
                        contents=prompt,
                        config={"response_mime_type": "application/json"},
                    ),
                )
        except genai_errors.APIError as exc:
            raise provider_status_error(_SERVICE, exc.code) from exc

        raw_text = response.text if response and response.text else "{}"
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ExternalServiceError(message="Invalid JSON response.", service=_SERVICE) from exc
        if not isinstance(data, dict):
            raise ExternalServiceError(message="Unexpected JSON response.", service=_SERVICE)
        return data