from src.adapters.persistence.models import PlantSpeciesModel
from src.domain.entities.plant_species import (
    EnrichmentSource,
    EnrichmentStatus,
    LightRequirement,
    PlantSpecies,
    SoilType,
)


class PlantSpeciesMapper:
    @staticmethod
    def to_domain(model: PlantSpeciesModel) -> PlantSpecies:
        return PlantSpecies(
            id=model.id,
            scientific_name=model.scientific_name,
            enrichment_status=EnrichmentStatus(model.enrichment_status) if isinstance(model.enrichment_status, str) else model.enrichment_status,
            family=model.family,
            genus=model.genus,
            order=model.order,
            plant_class=model.plant_class,
            common_names=tuple(model.common_names or []),
            provider_entity_id=getattr(model, "provider_entity_id", None),
            gbif_id=model.gbif_id,
            is_edible=model.is_edible,
            water_frequency_per_week=model.water_frequency_per_week,
            light_requirement=LightRequirement(model.light_requirement) if model.light_requirement else None,
            soil_type=SoilType(model.soil_type) if model.soil_type else None,
            best_planting_season=model.best_planting_season,
            origin_country=model.origin_country,
            habitat=model.habitat,
            enriched_at=model.enriched_at,
            enrichment_source=EnrichmentSource(model.enrichment_source) if model.enrichment_source else None,
        )

    @staticmethod
    def to_model(entity: PlantSpecies) -> PlantSpeciesModel:
        return PlantSpeciesModel(
            id=entity.id,
            scientific_name=entity.scientific_name,
            enrichment_status=entity.enrichment_status.value if hasattr(entity.enrichment_status, "value") else str(entity.enrichment_status),
            family=entity.family,
            genus=entity.genus,
            order=entity.order,
            plant_class=entity.plant_class,
            common_names=list(entity.common_names),
            provider_entity_id=entity.provider_entity_id,
            gbif_id=entity.gbif_id,
            is_edible=entity.is_edible,
            water_frequency_per_week=entity.water_frequency_per_week,
            light_requirement=entity.light_requirement.value if entity.light_requirement is not None and hasattr(entity.light_requirement, "value") else None,
            soil_type=entity.soil_type.value if entity.soil_type is not None and hasattr(entity.soil_type, "value") else None,
            best_planting_season=entity.best_planting_season,
            origin_country=entity.origin_country,
            habitat=entity.habitat,
            enriched_at=entity.enriched_at,
            enrichment_source=entity.enrichment_source.value if entity.enrichment_source is not None and hasattr(entity.enrichment_source, "value") else None,
        )