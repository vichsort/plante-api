import uuid
from datetime import date, datetime

from sqlalchemy import UUID, Date, DateTime, ForeignKey, Integer
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.quota.domain.value_objects.level import QuotaLevel
from src.shared.adapters import Base, enum_values, utcnow


class QuotaModel(Base):
    """
    One row per user who has spent tokens or was granted an extended quota; no row = standard. The
    key is the `user_id` itself (no `AuditMixin`: there is no own ID nor soft delete).
    """
    __tablename__ = "quotas"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    level: Mapped[QuotaLevel] = mapped_column(
        SAEnum(QuotaLevel, values_callable=enum_values, name="quotaLevel"),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tokens_used_today: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_day: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False,
    )
