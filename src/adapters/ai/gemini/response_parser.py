from src.domain.entities.plant_species import LightRequirement, SoilType
from src.domain.entities.health_record import HealthSeverity

class GeminiResponseParser:
    @staticmethod
    def parse_enrich_species(data: dict) -> dict:
        return {
            "common_names": tuple(data.get("common_names", [])),
            "is_edible": bool(data.get("is_edible")),
            "water_frequency_per_week": int(data.get("water_frequency_per_week", 0)),
            "light_requirement": LightRequirement(data["light_requirement"]) if data.get("light_requirement") else None,
            "soil_type": SoilType(data["soil_type"]) if data.get("soil_type") else None,
            "best_planting_season": data.get("best_planting_season"),
            "origin_country": data.get("origin_country"),
            "habitat": data.get("habitat"),
        }

    @staticmethod
    def parse_nutritional(data: dict) -> dict:
        return {
            "tea_preparation": data.get("tea_preparation"),
            "tea_benefits": data.get("tea_benefits"),
            "food_recipe_name": data.get("food_recipe_name"),
            "food_recipe_ingredients": tuple(data.get("food_recipe_ingredients", [])),
            "medicinal_uses": data.get("medicinal_uses"),
            "seasoning_pairings": data.get("seasoning_pairings"),
        }

    @staticmethod
    def parse_health_diagnosis(data: dict) -> dict:
        return {
            "severity": HealthSeverity(data.get("severity", "healthy")),
            "vitality_score": float(data.get("vitality_score", 1.0)),
            "issues_detected": tuple(data.get("issues_detected", [])),
            "treatment_plan": tuple(data.get("treatment_plan", [])),
            "recovery_estimate_days": data.get("recovery_estimate_days"),
        }