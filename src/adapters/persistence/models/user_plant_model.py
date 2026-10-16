import uuid
from datetime import date, datetime

from sqlalchemy import UUID, Boolean, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.entities.user_plant import IdentificationSource, IdentificationStatus

from .base import AuditMixin, Base, enum_values


class UserPlantModel(Base, AuditMixin):
    __tablename__ = "user_plants"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False)
    identification_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    identification_source: Mapped[IdentificationSource] = mapped_column(
        SAEnum(IdentificationSource, values_callable=enum_values, name="identificationSource"),
        nullable=False,
    )
    status: Mapped[IdentificationStatus] = mapped_column(
        SAEnum(IdentificationStatus, values_callable=enum_values, name="identificationStatus"),
        nullable=False,
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    primary_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_watered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Streak achatado
    streak_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_last_action_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # CareSchedule achatado (1-to-1 obrigatório, sem tabela separada)
    care_type: Mapped[str] = mapped_column(String(50), nullable=False)
    care_interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    care_is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Dia do calendário local (`LocalCalendar`), não instante
    care_next_due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    care_last_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    care_climate_adjusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    care_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)