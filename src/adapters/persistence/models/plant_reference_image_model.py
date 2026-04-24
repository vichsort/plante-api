from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Enum as SAEnum
from .base import Base
from src.domain.entities.plant_reference_image import ImageSource
from datetime import datetime

class PlantReferenceImageModel(Base):
    __tablename__ = "plant_reference_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(
        SAEnum(ImageSource, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)