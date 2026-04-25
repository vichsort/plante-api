from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Enum as SAEnum, JSON
from .base import Base
from src.domain.entities.health_record import HealthSeverity
from datetime import datetime

class HealthRecordModel(Base):
    __tablename__ = "health_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_plant_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    diagnosed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vitality_score: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(
        SAEnum(HealthSeverity, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    image_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issues_detected: Mapped[list | None] = mapped_column(JSON, nullable=True)
    treatment_plan: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recovery_estimate_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)