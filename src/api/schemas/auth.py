from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    country: str
    state: str

class RegisterResponse(BaseModel):
    user_id: str
    email: str
    status: str

class VerifyEmailRequest(BaseModel):
    user_id: str
    raw_code: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class MessageResponse(BaseModel):
    message: str