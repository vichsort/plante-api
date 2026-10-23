from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, StringConstraints

from src.modules.identity.domain.entities.user import User
from src.modules.identity.domain.use_cases.login import LoginResult
from src.modules.identity.domain.use_cases.refresh_token import RefreshResult

# Same rules as `UserLocation`, checked here so a bad value is a 422 and not a 500
Country = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z]{2}$")]  # ISO 3166-1 alpha-2
State = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]  # column size


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    country: Country
    state: State
    # The token the site's Turnstile widget produced; required when the API has the captcha on
    captcha_token: str | None = Field(default=None, max_length=2048)

class RegisterResponse(BaseModel):
    user_id: UUID
    email: str
    status: str

    @classmethod
    def from_domain(cls, user: User) -> "RegisterResponse":
        return cls(
            user_id=user.id,
            email=user.email,
            status="verified" if user.is_verified else "pending_verification",
        )

class VerifyEmailRequest(BaseModel):
    user_id: UUID
    raw_code: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    @classmethod
    def from_domain(cls, result: LoginResult | RefreshResult) -> "TokenResponse":
        return cls(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type=result.token_type,
        )

class RefreshRequest(BaseModel):
    refresh_token: str


class ChangeEmailRequest(BaseModel):
    current_password: str
    new_email: EmailStr

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class DeleteAccountRequest(BaseModel):
    password: str

class UpdateLocationRequest(BaseModel):
    country: Country
    state: State
