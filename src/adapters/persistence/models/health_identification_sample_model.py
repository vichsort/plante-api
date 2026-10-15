import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, UUID, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.entities.health_identification_sample import HealthSampleStatus

from .base import AuditMixin, Base


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
    reference_image_keys: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    vitality_score: Mapped[float] = mapped_column(Float, nullable=False)
    issues_detected: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    treatment_plan: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    identification_source: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_response: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum(HealthSampleStatus, values_callable=lambda e: [x.value for x in e], name="healthSampleStatus"),
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