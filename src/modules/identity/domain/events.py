from dataclasses import dataclass
from datetime import UTC, datetime

from src.shared.domain import DomainEvent, UserId


@dataclass(frozen=True)
class UserRegisteredEvent(DomainEvent):
    """Conta criada: dispara o e-mail com o código de verificação, quando a verificação está ligada."""
    user_id: UserId
    email: str
    requires_verification: bool

    @classmethod
    def create(cls, user_id: UserId, email: str, requires_verification: bool) -> "UserRegisteredEvent":
        return cls(
            occurred_on=datetime.now(UTC),
            user_id=user_id,
            email=email,
            requires_verification=requires_verification,
        )
