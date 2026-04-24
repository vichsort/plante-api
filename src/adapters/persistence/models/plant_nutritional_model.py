from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Enum as JSON
from .base import Base
from datetime import datetime

class PlantNutritionalModel(Base):
    __tablename__ = "plant_nutritional"

    scientific_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    tea_preparation: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    tea_benefits: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    food_recipe_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    food_recipe_ingredients: Mapped[list | None] = mapped_column(JSON, nullable=True)
    medicinal_uses: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    seasoning_pairings: Mapped[str | None] = mapped_column(String(500), nullable=True)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)