from src.domain.entities.plant_nutritional import PlantNutritional
from src.adapters.persistence.models import PlantNutritionalModel

class PlantNutritionalMapper:
    @staticmethod
    def to_domain(model: PlantNutritionalModel) -> PlantNutritional:
        return PlantNutritional(
            scientific_name=model.scientific_name,
            tea_preparation=model.tea_preparation,
            tea_benefits=model.tea_benefits,
            food_recipe_name=model.food_recipe_name,
            food_recipe_ingredients=tuple(model.food_recipe_ingredients or []),
            medicinal_uses=model.medicinal_uses,
            seasoning_pairings=model.seasoning_pairings,
            enriched_at=model.enriched_at,
        )

    @staticmethod
    def to_model(entity: PlantNutritional) -> PlantNutritionalModel:
        return PlantNutritionalModel(
            scientific_name=entity.scientific_name,
            tea_preparation=entity.tea_preparation,
            tea_benefits=entity.tea_benefits,
            food_recipe_name=entity.food_recipe_name,
            food_recipe_ingredients=list(entity.food_recipe_ingredients),
            medicinal_uses=entity.medicinal_uses,
            seasoning_pairings=entity.seasoning_pairings,
            enriched_at=entity.enriched_at,
        )