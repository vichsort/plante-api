from src.domain.entities.plant_species import (
    PlantSpecies, EnrichmentStatus, LightRequirement, SoilType, EnrichmentSource,
)
from src.adapters.persistence.models import PlantSpeciesModel

class PlantSpeciesMapper:
    @staticmethod
    def to_domain(model: PlantSpeciesModel) -> PlantSpecies:
        return PlantSpecies(
            id=model.id,
            scientific_name=model.scientific_name,
            enrichment_status=EnrichmentStatus(model.enrichment_status),
            family=model.family,
            genus=model.genus,
            order=model.order,
            plant_class=model.plant_class,
            common_names=tuple(model.common_names or []),
            kindwise_entity_id=model.kindwise_entity_id,
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
            enrichment_status=entity.enrichment_status.value,
            family=entity.family,
            genus=entity.genus,
            order=entity.order,
            plant_class=entity.plant_class,
            common_names=list(entity.common_names),
            kindwise_entity_id=entity.kindwise_entity_id,
            gbif_id=entity.gbif_id,
            is_edible=entity.is_edible,
            water_frequency_per_week=entity.water_frequency_per_week,
            light_requirement=entity.light_requirement.value if entity.light_requirement else None,
            soil_type=entity.soil_type.value if entity.soil_type else None,
            best_planting_season=entity.best_planting_season,
            origin_country=entity.origin_country,
            habitat=entity.habitat,
            enriched_at=entity.enriched_at,
            enrichment_source=entity.enrichment_source.value if entity.enrichment_source else None,
        )