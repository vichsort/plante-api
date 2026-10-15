import uuid
from datetime import datetime

from sqlalchemy import JSON, UUID, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.entities.health_identification_sample import HealthSampleStatus
from src.domain.value_objects.json_value import JsonObject

from .base import AuditMixin, Base, enum_values


class HealthIdentificationSampleModel(Base, AuditMixin):
    __tablename__ = "health_identification_samples"

    health_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("health_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_image_key: Mapped[str] = mapped_column(String(500), nullable=False)
    reference_image_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    vitality_score: Mapped[float] = mapped_column(Float, nullable=False)
    issues_detected: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    treatment_plan: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    identification_source: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_response: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    status: Mapped[HealthSampleStatus] = mapped_column(
        SAEnum(HealthSampleStatus, values_callable=enum_values, name="healthSampleStatus"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovery_estimate_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)