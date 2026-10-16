from src.modules.catalog.adapters.persistence.models.plant_species import (
    PlantSpeciesModel,
)
from src.modules.catalog.domain.entities.plant_species import PlantSpecies
from src.modules.catalog.domain.value_objects.ids import PlantSpeciesId


class PlantSpeciesMapper:
    @staticmethod
    def to_domain(model: PlantSpeciesModel) -> PlantSpecies:
        return PlantSpecies(
            id=PlantSpeciesId(model.id),
            scientific_name=model.scientific_name,
            enrichment_status=model.enrichment_status,
            family=model.family,
            genus=model.genus,
            order=model.order,
            plant_class=model.plant_class,
            common_names=tuple(model.common_names or []),
            provider_entity_id=model.kindwise_entity_id,
            gbif_id=model.gbif_id,
            is_edible=model.is_edible,
            water_frequency_per_week=model.water_frequency_per_week,
            light_requirement=model.light_requirement,
            soil_type=model.soil_type,
            best_planting_season=model.best_planting_season,
            origin_country=model.origin_country,
            habitat=model.habitat,
            enriched_at=model.enriched_at,
            enrichment_source=model.enrichment_source,
        )

    @staticmethod
    def to_model(entity: PlantSpecies) -> PlantSpeciesModel:
        return PlantSpeciesModel(
            id=entity.id,
            scientific_name=entity.scientific_name,
            enrichment_status=entity.enrichment_status,
            family=entity.family,
            genus=entity.genus,
            order=entity.order,
            plant_class=entity.plant_class,
            common_names=list(entity.common_names),
            # coluna com nome histórico: guarda o ID do provedor que identificou (Kindwise ou PlantNet)
            kindwise_entity_id=entity.provider_entity_id,
            gbif_id=entity.gbif_id,
            is_edible=entity.is_edible,
            water_frequency_per_week=entity.water_frequency_per_week,
            light_requirement=entity.light_requirement,
            soil_type=entity.soil_type,
            best_planting_season=entity.best_planting_season,
            origin_country=entity.origin_country,
            habitat=entity.habitat,
            enriched_at=entity.enriched_at,
            enrichment_source=entity.enrichment_source,
        )