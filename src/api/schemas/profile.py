from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from src.domain.entities.user import User
from src.domain.ports.achievement_repository import AchievementView


class ChangeEmailRequest(BaseModel):
    current_password: str
    new_email: EmailStr

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class UpdateLocationRequest(BaseModel):
    country: str
    state: str

class UpgradeSubscriptionRequest(BaseModel):
    plan_duration_days: int

class UpgradeSubscriptionResponse(BaseModel):
    user_id: UUID
    subscription: str
    expires_at: datetime | None

    @classmethod
    def from_domain(cls, user: User) -> "UpgradeSubscriptionResponse":
        return cls(
            user_id=user.id,
            subscription=user.subscription.plan_name,
            expires_at=user.subscription_expires_at,
        )

class AchievementItemResponse(BaseModel):
    id: UUID
    badge_code: str
    unlocked_at: datetime

    @classmethod
    def from_domain(cls, achievement: AchievementView) -> "AchievementItemResponse":
        return cls(
            id=achievement.id,
            badge_code=achievement.badge_code,
            unlocked_at=achievement.unlocked_at,
        )