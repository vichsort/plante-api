from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.subscription.domain.entities.subscription import Subscription


class UpgradeSubscriptionRequest(BaseModel):
    plan_duration_days: int


class UpgradeSubscriptionResponse(BaseModel):
    user_id: UUID
    subscription: str
    expires_at: datetime | None

    @classmethod
    def from_domain(cls, subscription: Subscription) -> "UpgradeSubscriptionResponse":
        return cls(
            user_id=subscription.user_id,
            subscription=subscription.tier.plan_name,
            expires_at=subscription.expires_at,
        )
