"""
catalog: o conhecimento sobre as espécies (README.md). A API pública é só domínio; a composição
monta o módulo por `src.modules.catalog.container`.
"""
from src.modules.catalog.domain.entities.nutritional import PlantNutritional
from src.modules.catalog.domain.entities.plant_species import (
    EnrichmentSource,
    EnrichmentStatus,
    LightRequirement,
    PlantSpecies,
    SoilType,
)
from src.modules.catalog.domain.entities.reference_image import (
    ImageSource,
    PlantReferenceImage,
)
from src.modules.catalog.domain.ports.species_enricher import (
    EnrichmentResult,
    ISpeciesEnricher,
    NutritionalEnrichmentResult,
)
from src.modules.catalog.domain.services.species_registry import ISpeciesRegistry
from src.modules.catalog.domain.value_objects.ids import (
    PlantSpeciesId,
    ReferenceImageId,
)

__all__ = [
    "EnrichmentResult",
    "EnrichmentSource",
    "EnrichmentStatus",
    "ISpeciesEnricher",
    "ISpeciesRegistry",
    "ImageSource",
    "LightRequirement",
    "NutritionalEnrichmentResult",
    "PlantNutritional",
    "PlantReferenceImage",
    "PlantSpecies",
    "PlantSpeciesId",
    "ReferenceImageId",
    "SoilType",
]
