from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True)
class PlantNutritional:
    scientific_name: str

    tea_preparation: str | None = None
    tea_benefits: str | None = None
    food_recipe_name: str | None = None
    food_recipe_ingredients: tuple[str, ...] = field(default_factory=tuple)
    medicinal_uses: str | None = None
    seasoning_pairings: str | None = None

    enriched_at: datetime | None = None

    def __post_init__(self):
        if not self.scientific_name:
            raise ValueError("scientific_name cannot be null.")

    @property
    def has_any_data(self) -> bool:
        """Retorna True se tem pelo menos um campo preenchido."""
        return any([
            self.tea_preparation,
            self.food_recipe_name,
            self.medicinal_uses,
            self.seasoning_pairings,
        ])