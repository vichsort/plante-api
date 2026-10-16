from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.catalog.domain.entities.plant_species import (
    EnrichmentSource,
    EnrichmentStatus,
    LightRequirement,
    SoilType,
)
from src.shared.adapters import AuditMixin, Base, enum_values


class PlantSpeciesModel(Base, AuditMixin):
    __tablename__ = "plant_species"

    scientific_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    enrichment_status: Mapped[EnrichmentStatus] = mapped_column(
        SAEnum(EnrichmentStatus, values_callable=enum_values, name="enrichmentStatus"),
        nullable=False,
        default=EnrichmentStatus.PENDING,
        index=True,
    )

    family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    genus: Mapped[str | None] = mapped_column(String(100), nullable=True)
    order: Mapped[str | None] = mapped_column(String(100), nullable=True)
    plant_class: Mapped[str | None] = mapped_column(String(100), nullable=True)
    common_names: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    kindwise_entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gbif_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_edible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    water_frequency_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    light_requirement: Mapped[LightRequirement | None] = mapped_column(
        SAEnum(LightRequirement, values_callable=enum_values, name="lightRequirement"),
        nullable=True,
    )
    soil_type: Mapped[SoilType | None] = mapped_column(
        SAEnum(SoilType, values_callable=enum_values, name="soilType"),
        nullable=True,
    )
    best_planting_season: Mapped[str | None] = mapped_column(String(50), nullable=True)
    origin_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    habitat: Mapped[str | None] = mapped_column(String(255), nullable=True)

    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enrichment_source: Mapped[EnrichmentSource | None] = mapped_column(
        SAEnum(EnrichmentSource, values_callable=enum_values, name="enrichmentSource"),
        nullable=True,
    )