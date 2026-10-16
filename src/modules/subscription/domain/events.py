from dataclasses import dataclass
from datetime import UTC, datetime

from src.shared.domain import DomainEvent, UserId


@dataclass(frozen=True)
class SubscriptionUpgradedEvent(DomainEvent):
    user_id: UserId
    plan_name: str
    expires_at: datetime

    @classmethod
    def create(cls, user_id: UserId, plan_name: str, expires_at: datetime) -> "SubscriptionUpgradedEvent":
        return cls(
            occurred_on=datetime.now(UTC),
            user_id=user_id,
            plan_name=plan_name,
            expires_at=expires_at,
        )
