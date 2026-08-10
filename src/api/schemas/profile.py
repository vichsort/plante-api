from pydantic import BaseModel, EmailStr


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
    user_id: str
    subscription: str
    expires_at: str

class AchievementItemResponse(BaseModel):
    id: str
    badge_code: str
    unlocked_at: str