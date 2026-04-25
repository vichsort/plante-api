from fastapi import APIRouter, Depends
from dependency_injector.wiring import Provide, inject

from src.infrastructure.container import Container
from src.api.deps import get_current_user_id
from src.api.response import ApiResponse
from src.api.schemas.auth import (
    RegisterRequest,
    VerifyEmailRequest,
    LoginRequest,
    RefreshRequest,
)
from src.domain.use_cases.register_user_use_case import RegisterUserUseCase, RegisterUserInputDTO
from src.domain.use_cases.verify_email_use_case import VerifyEmailUseCase, VerifyEmailInputDTO
from src.domain.use_cases.login_use_case import LoginUseCase
from src.domain.use_cases.refresh_token_use_case import RefreshTokenUseCase
from src.domain.use_cases.logout_use_case import LogoutUseCase

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", status_code=201)
@inject
async def register(
    body: RegisterRequest,
    use_case: RegisterUserUseCase = Depends(Provide[Container.register_user_use_case]),
) -> ApiResponse:
    result = await use_case.execute(RegisterUserInputDTO(
        email=body.email,
        password=body.password,
        country=body.country,
        state=body.state,
    ))
    return ApiResponse.ok(result)

@router.post("/verify-email", status_code=200)
@inject
async def verify_email(
    body: VerifyEmailRequest,
    use_case: VerifyEmailUseCase = Depends(Provide[Container.verify_email_use_case]),
) -> ApiResponse:
    result = await use_case.execute(VerifyEmailInputDTO(
        user_id=body.user_id,
        raw_code=body.raw_code,
    ))
    return ApiResponse.ok(result)

@router.post("/login", status_code=200)
@inject
async def login(
    body: LoginRequest,
    use_case: LoginUseCase = Depends(Provide[Container.login_use_case]),
) -> ApiResponse:
    result = await use_case.execute(
        email=body.email,
        password=body.password,
    )
    return ApiResponse.ok(result)

@router.post("/refresh", status_code=200)
@inject
async def refresh(
    body: RefreshRequest,
    use_case: RefreshTokenUseCase = Depends(Provide[Container.refresh_token_use_case]),
) -> ApiResponse:
    result = await use_case.execute(refresh_token=body.refresh_token)
    return ApiResponse.ok(result)

@router.post("/logout", status_code=200)
@inject
async def logout(
    use_case: LogoutUseCase = Depends(Provide[Container.logout_use_case]),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse:
    await use_case.execute(user_id=user_id)
    return ApiResponse.ok({"message": "Logged out successfully."})