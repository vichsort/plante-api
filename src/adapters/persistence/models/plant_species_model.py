from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Integer, DateTime, Enum as SAEnum, JSON
from .base import Base
from src.domain.entities.plant_species import EnrichmentStatus, LightRequirement, SoilType, EnrichmentSource
from datetime import datetime

class PlantSpeciesModel(Base):
    __tablename__ = "plant_species"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scientific_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    enrichment_status: Mapped[str] = mapped_column(
        SAEnum(EnrichmentStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=EnrichmentStatus.PENDING.value,
        index=True,
    )

    family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    genus: Mapped[str | None] = mapped_column(String(100), nullable=True)
    order: Mapped[str | None] = mapped_column(String(100), nullable=True)
    plant_class: Mapped[str | None] = mapped_column(String(100), nullable=True)
    common_names: Mapped[list | None] = mapped_column(JSON, nullable=True)

    kindwise_entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gbif_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_edible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    water_frequency_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    light_requirement: Mapped[str | None] = mapped_column(
        SAEnum(LightRequirement, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    soil_type: Mapped[str | None] = mapped_column(
        SAEnum(SoilType, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    best_planting_season: Mapped[str | None] = mapped_column(String(50), nullable=True)
    origin_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    habitat: Mapped[str | None] = mapped_column(String(255), nullable=True)

    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enrichment_source: Mapped[str | None] = mapped_column(
        SAEnum(EnrichmentSource, values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )