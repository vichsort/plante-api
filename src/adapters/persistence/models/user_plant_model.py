from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Boolean, Enum as SAEnum
from .base import Base
from src.domain.entities.user_plant import IdentificationStatus, IdentificationSource
from datetime import datetime

class UserPlantModel(Base):
    __tablename__ = "user_plants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False)
    identification_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    identification_source: Mapped[str] = mapped_column(
        SAEnum(IdentificationSource, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        SAEnum(IdentificationStatus, values_callable=lambda e: [x.value for x in e]),
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
    care_next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    care_last_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    care_climate_adjusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    care_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)