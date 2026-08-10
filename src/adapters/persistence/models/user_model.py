from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.value_objects.subscription_tier import SubscriptionTier

from .base import AuditMixin, Base


class UserModel(Base, AuditMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # UserLocation achatado — VO não tem identidade própria no banco
    location_country: Mapped[str] = mapped_column(String(2), nullable=False)
    location_state: Mapped[str] = mapped_column(String(100), nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscription: Mapped[str] = mapped_column(
        SAEnum(SubscriptionTier, values_callable=lambda e: [x.plan_name for x in e], name="subscriptionTier"),
        nullable=False,
        default=SubscriptionTier.FREE.plan_name,
    )
    tokens_used_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    garden_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    fcm_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fcm_token_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)