import uuid

from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.entities.plant_reference_image import ImageSource

from .base import AuditMixin, Base, enum_values


class PlantReferenceImageModel(Base, AuditMixin):
    __tablename__ = "plant_reference_images"

    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[ImageSource] = mapped_column(
        SAEnum(ImageSource, values_callable=enum_values, name="imageSource"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )