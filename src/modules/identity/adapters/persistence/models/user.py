from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.adapters import AuditMixin, Base


class UserModel(Base, AuditMixin):
    __tablename__ = "users"
    # O domínio normaliza (`normalize_email`); o banco garante que nada grave fora da forma canônica
    __table_args__ = (CheckConstraint("email = lower(btrim(email))", name="ck_users_email_normalized"),)

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # Troca de e-mail aguardando o código (a unicidade é conferida de novo na confirmação)
    pending_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # UserLocation achatado — VO não tem identidade própria no banco
    location_country: Mapped[str] = mapped_column(String(2), nullable=False)
    location_state: Mapped[str] = mapped_column(String(100), nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Last version of the terms accepted, and when (LGPD: the consent is on record)
    terms_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)