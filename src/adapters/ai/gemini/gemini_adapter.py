from google import genai
from src.domain.ports.plant_enricher import IPlantEnricher
from src.adapters.ai.gemini.prompt_builder import GeminiPromptBuilder
from src.adapters.ai.gemini.response_parser import GeminiResponseParser

_MODEL = "gemini-2.5-flash"

class GeminiAdapter(IPlantEnricher):
    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._builder = GeminiPromptBuilder()
        self._parser = GeminiResponseParser()

    async def enrich_species(self, scientific_name: str) -> dict:
        prompt = GeminiPromptBuilder.enrich_species(scientific_name)
        raw = await self._generate(prompt)
        return GeminiResponseParser.parse_enrich_species(raw)

    async def get_nutritional_data(self, scientific_name: str) -> dict:
        prompt = GeminiPromptBuilder.nutritional_analysis(scientific_name)
        raw = await self._generate(prompt)
        return GeminiResponseParser.parse_nutritional(raw)

    async def diagnose_health(self, scientific_name: str, issues: list[str]) -> dict:
        prompt = GeminiPromptBuilder.health_diagnosis(scientific_name, issues)
        raw = await self._generate(prompt)
        return GeminiResponseParser.parse_health_diagnosis(raw)

    async def _generate(self, prompt: str) -> dict:
        import asyncio
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._client.models.generate_content(
                model=_MODEL,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            ),
        )
        import json
        return json.loads(response.text)