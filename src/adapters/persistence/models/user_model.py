from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.value_objects.subscription_tier import SubscriptionTier

from .base import AuditMixin, Base


def _plan_names(_: type[Enum]) -> list[str]:
    """`values_callable` do SAEnum: o banco guarda o nome do plano ("FREE", "PRO")."""
    return [tier.plan_name for tier in SubscriptionTier]


class UserModel(Base, AuditMixin):
    __tablename__ = "users"
    # O domínio normaliza (`normalize_email`); o banco garante que nada grave fora da forma canônica
    __table_args__ = (CheckConstraint("email = lower(btrim(email))", name="ck_users_email_normalized"),)

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # UserLocation achatado — VO não tem identidade própria no banco
    location_country: Mapped[str] = mapped_column(String(2), nullable=False)
    location_state: Mapped[str] = mapped_column(String(100), nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    subscription: Mapped[SubscriptionTier] = mapped_column(
        SAEnum(SubscriptionTier, values_callable=_plan_names, name="subscriptionTier"),
        nullable=False,
        default=SubscriptionTier.FREE,
    )
    tokens_used_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)