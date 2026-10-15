from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.api.deps import CurrentUserId
from src.api.openapi import error_responses
from src.api.response import ApiResponse
from src.api.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    VerifyEmailRequest,
)
from src.domain.exceptions import UnauthorizedError
from src.domain.use_cases.login_use_case import LoginUseCase
from src.domain.use_cases.logout_use_case import LogoutUseCase
from src.domain.use_cases.refresh_token_use_case import RefreshTokenUseCase
from src.domain.use_cases.register_user_use_case import (
    RegisterUserInputDTO,
    RegisterUserUseCase,
)
from src.domain.use_cases.verify_email_use_case import (
    VerifyEmailInputDTO,
    VerifyEmailUseCase,
)
from src.domain.value_objects.ids import UserId
from src.infrastructure.container import Container

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=201,
    response_model=ApiResponse[RegisterResponse],
    responses=error_responses(*RegisterUserUseCase.raises),
)
@inject
async def register(
    body: RegisterRequest,
    use_case: Annotated[RegisterUserUseCase, Depends(Provide[Container.use_cases.register_user_use_case])],
) -> ApiResponse[RegisterResponse]:
    user = await use_case.execute(RegisterUserInputDTO(
        email=body.email,
        password=body.password,
        country=body.country,
        state=body.state,
    ))
    return ApiResponse.success(RegisterResponse.from_domain(user))


@router.post(
    "/verify-email",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(*VerifyEmailUseCase.raises),
)
@inject
async def verify_email(
    body: VerifyEmailRequest,
    use_case: Annotated[VerifyEmailUseCase, Depends(Provide[Container.use_cases.verify_email_use_case])],
) -> ApiResponse[MessageResponse]:
    await use_case.execute(VerifyEmailInputDTO(
        user_id=UserId(body.user_id),
        raw_code=body.raw_code,
    ))
    return ApiResponse.success(MessageResponse(message="Email verified successfully."))


@router.post(
    "/login",
    status_code=200,
    response_model=ApiResponse[TokenResponse],
    responses=error_responses(*LoginUseCase.raises),
)
@inject
async def login(
    body: LoginRequest,
    use_case: Annotated[LoginUseCase, Depends(Provide[Container.use_cases.login_use_case])],
) -> ApiResponse[TokenResponse]:
    result = await use_case.execute(email=body.email, password=body.password)
    return ApiResponse.success(TokenResponse.from_domain(result))


@router.post(
    "/refresh",
    status_code=200,
    response_model=ApiResponse[TokenResponse],
    responses=error_responses(*RefreshTokenUseCase.raises),
)
@inject
async def refresh(
    body: RefreshRequest,
    use_case: Annotated[RefreshTokenUseCase, Depends(Provide[Container.use_cases.refresh_token_use_case])],
) -> ApiResponse[TokenResponse]:
    result = await use_case.execute(refresh_token=body.refresh_token)
    return ApiResponse.success(TokenResponse.from_domain(result))


@router.post(
    "/logout",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(UnauthorizedError),
)
@inject
async def logout(
    use_case: Annotated[LogoutUseCase, Depends(Provide[Container.use_cases.logout_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[MessageResponse]:
    await use_case.execute(user_id=user_id)
    return ApiResponse.success(MessageResponse(message="Logged out successfully."))
