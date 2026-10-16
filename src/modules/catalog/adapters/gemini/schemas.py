"""
Formato das respostas do Gemini para o catálogo, enviado como `response_schema` (saída
estruturada): o Gemini é obrigado a responder nesse formato, e a resposta é validada com ele.
"""
from pydantic import BaseModel, ConfigDict

from src.modules.catalog.domain.entities.plant_species import LightRequirement, SoilType


class _Schema(BaseModel):
    model_config = ConfigDict(frozen=True)


class SpeciesEnrichmentSchema(_Schema):
    common_names: list[str]
    is_edible: bool
    water_frequency_per_week: int
    light_requirement: LightRequirement
    soil_type: SoilType
    best_planting_season: str
    origin_country: str
    habitat: str


class NutritionalAnalysisSchema(_Schema):
    tea_preparation: str | None
    tea_benefits: str | None
    food_recipe_name: str | None
    food_recipe_ingredients: list[str]
    medicinal_uses: str | None
    seasoning_pairings: str | None
