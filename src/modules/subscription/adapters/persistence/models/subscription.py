import uuid
from datetime import date, datetime
from enum import Enum

from sqlalchemy import UUID, Date, DateTime, ForeignKey, Integer
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.modules.subscription.domain.value_objects.tier import SubscriptionTier
from src.shared.adapters import Base, utcnow


def _plan_names(_: type[Enum]) -> list[str]:
    """`values_callable` do SAEnum: o banco guarda o nome do plano ("FREE", "PRO")."""
    return [tier.plan_name for tier in SubscriptionTier]


class SubscriptionModel(Base):
    """
    Uma linha por usuário que já gastou tokens; sem linha = FREE. A chave é o
    próprio `user_id` (sem `AuditMixin`: não há ID próprio nem exclusão lógica).
    """
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # Mesmo tipo do Postgres que a coluna `users.subscription` usava
    tier: Mapped[SubscriptionTier] = mapped_column(
        SAEnum(SubscriptionTier, values_callable=_plan_names, name="subscriptionTier"),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tokens_used_today: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_day: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False,
    )
