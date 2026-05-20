from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class EnrichmentStatus(Enum):
    PENDING = "pending"
    ENRICHED = "enriched"
    FAILED = "failed"

class LightRequirement(Enum):
    LOW = "low"
    INDIRECT = "indirect"
    DIRECT = "direct"
    FULL_SUN = "full_sun"

class SoilType(Enum):
    SANDY = "sandy"
    CLAY = "clay"
    LOAMY = "loamy"
    WELL_DRAINING = "well_draining"

class EnrichmentSource(Enum):
    GEMINI = "gemini"
    KINDWISE = "kindwise"
    PLANTNET = "plantnet"

@dataclass(frozen=True)
class PlantSpecies:
    scientific_name: str
    enrichment_status: EnrichmentStatus
    id: int | None = None

    # Taxonomia — vem do PlantNet/Kindwise na identificação
    family: str | None = None
    genus: str | None = None
    order: str | None = None
    plant_class: str | None = None
    common_names: tuple[str, ...] = field(default_factory=tuple)

    # IDs externos
    provider_entity_id: str | None = None
    gbif_id: str | None = None

    # Cuidados — vem do Gemini
    is_edible: bool | None = None
    water_frequency_per_week: int | None = None
    light_requirement: LightRequirement | None = None
    soil_type: SoilType | None = None
    best_planting_season: str | None = None
    origin_country: str | None = None
    habitat: str | None = None

    # Controle de enriquecimento
    enriched_at: datetime | None = None
    enrichment_source: EnrichmentSource | None = None

    def __post_init__(self):
        if not self.scientific_name:
            raise ValueError("scientific_name cannot be null.")

    @property
    def is_enriched(self) -> bool:
        return self.enrichment_status == EnrichmentStatus.ENRICHED

    @property
    def has_basic_taxonomy(self) -> bool:
        return self.family is not None and self.genus is not None

    @classmethod
    def create_skeleton(
        cls,
        scientific_name: str,
        family: str | None = None,
        genus: str | None = None,
        common_names: tuple[str, ...] = (),
        provider_entity_id: str | None = None,
        gbif_id: str | None = None,
    ) -> "PlantSpecies":
        """Cria uma espécie com dados mínimos vindos da identificação. Aguarda enriquecimento pelo Gemini."""
        return cls(
            scientific_name=scientific_name,
            enrichment_status=EnrichmentStatus.PENDING,
            family=family,
            genus=genus,
            common_names=common_names,
            provider_entity_id=provider_entity_id,
            gbif_id=gbif_id,
        )