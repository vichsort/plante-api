from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from src.modules.identity.domain.value_objects.email import normalize_email
from src.modules.identity.domain.value_objects.user_location import UserLocation
from src.shared.domain import UserId

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
    created_at: datetime | None = None
    # Novo e-mail aguardando o código: o atual continua valendo até a confirmação
    pending_email: str | None = None
    bio: str | None = None
    profile_picture_url: str | None = None
    # Last version of the terms the user accepted, and when (LGPD: the consent is on record)
    terms_version: str | None = None
    terms_accepted_at: datetime | None = None

    def __post_init__(self) -> None:
        self.email = normalize_email(self.email)
        self._assert_valid_email(self.email)

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
            created_at=current_time,
        )

    def verify_email(self) -> None:
        self.is_verified = True

    def accept_terms(self, version: str, at: datetime) -> None:
        self.terms_version = version
        self.terms_accepted_at = at

    def has_accepted(self, version: str) -> bool:
        return self.terms_version == version

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