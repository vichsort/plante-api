from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from src.modules.identity.api.schemas import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UpdateLocationRequest,
    VerifyEmailRequest,
)
from src.modules.identity.container import IdentityContainer
from src.modules.identity.domain.use_cases.change_email import (
    ChangeEmailInputDTO,
    ChangeEmailUseCase,
)
from src.modules.identity.domain.use_cases.change_password import (
    ChangePasswordInputDTO,
    ChangePasswordUseCase,
)
from src.modules.identity.domain.use_cases.login import LoginUseCase
from src.modules.identity.domain.use_cases.logout import LogoutUseCase
from src.modules.identity.domain.use_cases.refresh_token import RefreshTokenUseCase
from src.modules.identity.domain.use_cases.register_user import (
    RegisterUserInputDTO,
    RegisterUserUseCase,
)
from src.modules.identity.domain.use_cases.update_location import (
    UpdateLocationFallbackInputDTO,
    UpdateLocationFallbackUseCase,
)
from src.modules.identity.domain.use_cases.verify_email import (
    VerifyEmailInputDTO,
    VerifyEmailUseCase,
)
from src.shared.api import ApiResponse, CurrentUserId, MessageResponse, error_responses
from src.shared.domain import UnauthorizedError, UserId

auth_router = APIRouter(prefix="/auth", tags=["auth"])
# Sob `/profile`, a tela "Meu perfil" do cliente (outros módulos também registram rotas ali)
profile_router = APIRouter(prefix="/profile", tags=["profile"], responses=error_responses(UnauthorizedError))


@auth_router.post(
    "/register",
    status_code=201,
    response_model=ApiResponse[RegisterResponse],
    responses=error_responses(*RegisterUserUseCase.raises),
)
@inject
async def register(
    body: RegisterRequest,
    use_case: Annotated[RegisterUserUseCase, Depends(Provide[IdentityContainer.register_user_use_case])],
) -> ApiResponse[RegisterResponse]:
    user = await use_case.execute(RegisterUserInputDTO(
        email=body.email,
        password=body.password,
        country=body.country,
        state=body.state,
    ))
    return ApiResponse.success(RegisterResponse.from_domain(user))


@auth_router.post(
    "/verify-email",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(*VerifyEmailUseCase.raises),
)
@inject
async def verify_email(
    body: VerifyEmailRequest,
    use_case: Annotated[VerifyEmailUseCase, Depends(Provide[IdentityContainer.verify_email_use_case])],
) -> ApiResponse[MessageResponse]:
    await use_case.execute(VerifyEmailInputDTO(
        user_id=UserId(body.user_id),
        raw_code=body.raw_code,
    ))
    return ApiResponse.success(MessageResponse(message="Email verified successfully."))


@auth_router.post(
    "/login",
    status_code=200,
    response_model=ApiResponse[TokenResponse],
    responses=error_responses(*LoginUseCase.raises),
)
@inject
async def login(
    body: LoginRequest,
    use_case: Annotated[LoginUseCase, Depends(Provide[IdentityContainer.login_use_case])],
) -> ApiResponse[TokenResponse]:
    result = await use_case.execute(email=body.email, password=body.password)
    return ApiResponse.success(TokenResponse.from_domain(result))


@auth_router.post(
    "/refresh",
    status_code=200,
    response_model=ApiResponse[TokenResponse],
    responses=error_responses(*RefreshTokenUseCase.raises),
)
@inject
async def refresh(
    body: RefreshRequest,
    use_case: Annotated[RefreshTokenUseCase, Depends(Provide[IdentityContainer.refresh_token_use_case])],
) -> ApiResponse[TokenResponse]:
    result = await use_case.execute(refresh_token=body.refresh_token)
    return ApiResponse.success(TokenResponse.from_domain(result))


@auth_router.post(
    "/logout",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(UnauthorizedError),
)
@inject
async def logout(
    use_case: Annotated[LogoutUseCase, Depends(Provide[IdentityContainer.logout_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[MessageResponse]:
    await use_case.execute(user_id=user_id)
    return ApiResponse.success(MessageResponse(message="Logged out successfully."))


@profile_router.patch(
    "/email",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(*ChangeEmailUseCase.raises),
)
@inject
async def change_email(
    body: ChangeEmailRequest,
    use_case: Annotated[ChangeEmailUseCase, Depends(Provide[IdentityContainer.change_email_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[MessageResponse]:
    await use_case.execute(ChangeEmailInputDTO(
        user_id=user_id,
        current_password=body.current_password,
        new_email=body.new_email,
    ))
    return ApiResponse.success(MessageResponse(message="Verification code sent to new email."))


@profile_router.patch(
    "/password",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(*ChangePasswordUseCase.raises),
)
@inject
async def change_password(
    body: ChangePasswordRequest,
    use_case: Annotated[ChangePasswordUseCase, Depends(Provide[IdentityContainer.change_password_use_case])],
    user_id: CurrentUserId,
) -> ApiResponse[MessageResponse]:
    await use_case.execute(ChangePasswordInputDTO(
        user_id=user_id,
        current_password=body.current_password,
        new_password=body.new_password,
    ))
    return ApiResponse.success(MessageResponse(message="Password updated successfully."))


@profile_router.patch(
    "/location",
    status_code=200,
    response_model=ApiResponse[MessageResponse],
    responses=error_responses(*UpdateLocationFallbackUseCase.raises),
)
@inject
async def update_location(
    body: UpdateLocationRequest,
    use_case: Annotated[
        UpdateLocationFallbackUseCase,
        Depends(Provide[IdentityContainer.update_location_use_case]),
    ],
    user_id: CurrentUserId,
) -> ApiResponse[MessageResponse]:
    await use_case.execute(UpdateLocationFallbackInputDTO(
        user_id=user_id,
        country=body.country,
        state=body.state,
    ))
    return ApiResponse.success(MessageResponse(message="Location updated successfully."))


# Um router só para a composição incluir
router = APIRouter()
router.include_router(auth_router)
router.include_router(profile_router)
