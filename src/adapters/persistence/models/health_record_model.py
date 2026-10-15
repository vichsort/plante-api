import uuid
from datetime import datetime

from sqlalchemy import JSON, UUID, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.entities.health_record import HealthSeverity

from .base import AuditMixin, Base, enum_values


class HealthRecordModel(Base, AuditMixin):
    __tablename__ = "health_records"

    user_plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_plants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Vínculo de mão única com a amostra de treino de saúde (que não aponta de volta)
    training_sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_health_samples.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    diagnosed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vitality_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[HealthSeverity] = mapped_column(
        SAEnum(HealthSeverity, values_callable=enum_values, name="healthSeverity"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    image_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issues_detected: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    treatment_plan: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    recovery_estimate_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)