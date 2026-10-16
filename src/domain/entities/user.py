from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from uuid import uuid4

from src.domain.value_objects.email import normalize_email
from src.domain.value_objects.ids import UserId
from src.domain.value_objects.subscription_tier import FeatureCost, SubscriptionTier
from src.domain.value_objects.user_location import UserLocation

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

@dataclass(slots=True)
class User:
    """
    Agregado raiz do usuário.
    Todas as mutações de estado passam por métodos — nunca por atribuição direta.
    """

    id: UserId
    email: str
    hashed_password: str
    location: UserLocation
    is_verified: bool
    subscription: SubscriptionTier
    created_at: datetime | None = None
    tokens_used_today: int = 0
    # Dia local a que `tokens_used_today` se refere: em outro dia o contador vale zero
    tokens_day: date | None = None
    # Novo e-mail aguardando o código: o atual continua valendo até a confirmação
    pending_email: str | None = None
    subscription_expires_at: datetime | None = None
    bio: str | None = None
    profile_picture_url: str | None = None

    def __post_init__(self) -> None:
        self.email = normalize_email(self.email)
        self._assert_valid_email(self.email)

        if self.tokens_used_today < 0:
            raise ValueError("tokens_used_today cannot be negative.")
        if self.subscription == SubscriptionTier.PRO and self.subscription_expires_at is None:
            raise ValueError("PRO subscription requires an expiration date.")

    @classmethod
    def create_new(
        cls,
        email: str,
        hashed_password: str,
        location: UserLocation,
        current_time: datetime,
    ) -> User:
        """Único ponto de entrada para criação de um novo usuário."""
        return cls(
            id=UserId(uuid4()),
            email=email,
            hashed_password=hashed_password,
            location=location,
            is_verified=False,
            subscription=SubscriptionTier.FREE,
            created_at=current_time,
        )

    def verify_email(self) -> None:
        self.is_verified = True

    def tokens_used_on(self, today: date) -> int:
        """A cota é diária: o contador gravado só vale no dia a que se refere."""
        return self.tokens_used_today if self.tokens_day == today else 0

    def consume_tokens(self, cost: FeatureCost, today: date) -> None:
        """Zera ao virar o dia na primeira cobrança, sem cron (quem decide se pode é a política)."""
        self.tokens_used_today = self.tokens_used_on(today) + cost.value
        self.tokens_day = today

    def update_location(self, new_location: UserLocation) -> None:
        self.location = new_location

    def request_email_change(self, new_email: str) -> None:
        new_email = normalize_email(new_email)
        self._assert_valid_email(new_email)
        self.pending_email = new_email

    def confirm_email_change(self) -> None:
        """O código chegou ao endereço novo: ele passa a ser o e-mail da conta, já verificado."""
        if self.pending_email is None:
            raise ValueError("There is no pending email change.")
        self.email = self.pending_email
        self.pending_email = None

    def change_password(self, new_hashed_password: str) -> None:
        if not new_hashed_password:
            raise ValueError("hashed_password cannot be empty.")
        self.hashed_password = new_hashed_password

    def upgrade_to_pro(self, expires_at: datetime, current_time: datetime) -> None:
        if expires_at <= current_time:
            raise ValueError("expires_at must be a future datetime.")
        self.subscription = SubscriptionTier.PRO
        self.subscription_expires_at = expires_at
        self.tokens_used_today = 0  # o upgrade começa com a cota do PRO cheia

    def is_pro(self, current_time: datetime) -> bool:
        return (
            self.subscription == SubscriptionTier.PRO
            and self.subscription_expires_at is not None
            and current_time < self.subscription_expires_at
        )

    def get_active_tier(self, current_time: datetime) -> SubscriptionTier:
        return SubscriptionTier.PRO if self.is_pro(current_time) else SubscriptionTier.FREE

    @staticmethod
    def _assert_valid_email(value: str) -> None:
        if not value or not _EMAIL_RE.match(value):
            raise ValueError(f"Invalid email address: '{value}'.")

    @staticmethod
    def _assert_valid_country(value: str) -> None:
        if len(value) != 2:
            raise ValueError(
                f"Invalid country '{value}'. Expected ISO 3166-1 alpha-2 (e.g., 'BR')."
            )

    @staticmethod
    def _assert_valid_state(value: str) -> None:
        if len(value) < 2:
            raise ValueError(f"Invalid state '{value}'. Minimum 2 characters.")