"""
Formato das respostas do Gemini. Os modelos são enviados como `response_schema` (saída
estruturada): o Gemini é obrigado a responder nesse formato, e a resposta é validada com eles.
Sem restrições numéricas (`ge`/`le`) no schema: o Gemini não as suporta; a faixa é conferida
na conversão para o domínio.
"""
from pydantic import BaseModel, ConfigDict

from src.domain.entities.plant_species import LightRequirement, SoilType
from src.modules.training import HealthSeverity


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


class HealthDiagnosisSchema(_Schema):
    severity: HealthSeverity
    vitality_score: float
    issues_detected: list[str]
    treatment_plan: list[str]
    recovery_estimate_days: int | None
    notes: str | None
