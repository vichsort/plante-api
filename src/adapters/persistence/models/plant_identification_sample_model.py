import uuid
from datetime import datetime

from sqlalchemy import JSON, UUID, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.value_objects.json_value import JsonObject

from .base import AuditMixin, Base


class PlantIdentificationSampleModel(Base, AuditMixin):
    __tablename__ = "plant_identification_samples"

    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    species_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plant_species.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_image_key: Mapped[str] = mapped_column(String(500), nullable=False)
    identification_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    identification_source: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_response: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    has_deep_analysis: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_nutritional_analysis: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)