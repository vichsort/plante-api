from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Boolean, Enum as JSON
from .base import Base
from datetime import datetime

class PlantIdentificationSampleModel(Base):
    __tablename__ = "plant_identification_samples"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    species_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_image_key: Mapped[str] = mapped_column(String(500), nullable=False)
    identification_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    identification_source: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_response: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    has_deep_analysis: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_nutritional_analysis: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)