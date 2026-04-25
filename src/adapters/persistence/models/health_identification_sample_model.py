from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum as SAEnum
from src.adapters.persistence.models.base import Base
from src.domain.entities.health_identification_sample import HealthSampleStatus

class HealthIdentificationSampleModel(Base):
    __tablename__ = "health_identification_samples"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    health_record_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("health_records.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        unique=True,   # 1 sample por health_record
    )
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_image_key: Mapped[str] = mapped_column(String(500), nullable=False)
    reference_image_keys: Mapped[list] = mapped_column(JSON, nullable=False)  # lista de storage keys
    vitality_score: Mapped[float] = mapped_column(Float, nullable=False)
    issues_detected: Mapped[list] = mapped_column(JSON, nullable=False)
    treatment_plan: Mapped[list] = mapped_column(JSON, nullable=False)
    identification_source: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_response: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum(HealthSampleStatus, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovery_estimate_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)