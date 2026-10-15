import uuid

from sqlalchemy import UUID, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import AuditMixin, Base


class IdentificationModel(Base, AuditMixin):
    """Histórico de identificações do usuário (dado pessoal: apagado com ele)."""

    __tablename__ = "identifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Vínculo de mão única: a amostra de treino não aponta de volta e nunca é apagada
    training_sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_identification_samples.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    species_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plant_species.id", ondelete="RESTRICT"),
        nullable=False,
    )
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    image_key: Mapped[str] = mapped_column(String(500), nullable=False)
