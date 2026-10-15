from uuid import UUID

from pydantic import BaseModel, EmailStr

from src.domain.entities.user import User
from src.domain.use_cases.login_use_case import LoginResult
from src.domain.use_cases.refresh_token_use_case import RefreshResult


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    country: str
    state: str

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

class MessageResponse(BaseModel):
    message: str
