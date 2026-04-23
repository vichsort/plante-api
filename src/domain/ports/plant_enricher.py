from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class EnrichmentResult:
    scientific_name: str
    source: str
    is_edible: bool | None = None
    water_frequency_per_week: int | None = None
    light_requirement: str | None = None
    soil_type: str | None = None
    best_planting_season: str | None = None
    origin_country: str | None = None
    habitat: str | None = None
    popular_names: tuple[str, ...] = ()
    description: str | None = None

@dataclass(frozen=True)
class NutritionalEnrichmentResult:
    scientific_name: str
    source: str
    tea_preparation: str | None = None
    tea_benefits: str | None = None
    food_recipe_name: str | None = None
    food_recipe_ingredients: tuple[str, ...] = ()
    medicinal_uses: str | None = None
    seasoning_pairings: str | None = None

@dataclass(frozen=True)
class DiseaseAnalysisResult:
    scientific_name: str
    disease_name: str
    source: str
    symptoms: tuple[str, ...] = ()
    treatment_steps: tuple[str, ...] = ()
    recovery_estimate_days: int | None = None

class IPlantEnricher(ABC):
    @abstractmethod
    async def enrich_species(self, scientific_name: str) -> EnrichmentResult:
        """Enriquece dados de cuidado de uma espécie pelo nome científico."""
        ...

    @abstractmethod
    async def enrich_nutritional(self, scientific_name: str) -> NutritionalEnrichmentResult:
        """Enriquece dados nutricionais e medicinais de uma espécie."""
        ...

    @abstractmethod
    async def analyze_disease(
        self, scientific_name: str, disease_name: str
    ) -> DiseaseAnalysisResult:
        """Analisa uma doença específica diagnosticada numa planta."""
        ...