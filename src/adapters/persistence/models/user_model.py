from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Integer, DateTime, Enum as SAEnum
from .base import Base
from src.domain.value_objects.subscription_tier import SubscriptionTier
from datetime import datetime

class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # UserLocation achatado — VO não tem identidade própria no banco
    location_country: Mapped[str] = mapped_column(String(2), nullable=False)
    location_state: Mapped[str] = mapped_column(String(100), nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscription: Mapped[str] = mapped_column(
        SAEnum(SubscriptionTier, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=SubscriptionTier.FREE.value,
    )
    tokens_used_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    garden_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    fcm_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fcm_token_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)