from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.domain.exceptions import UnauthorizedError
from src.domain.ports.token_service import ITokenService, TokenKind
from src.domain.value_objects.ids import UserId
from src.infrastructure.container import Container

_bearer = HTTPBearer(auto_error=False)


@inject
async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    token_service: Annotated[ITokenService, Depends(Provide[Container.adapters.token_service])],
) -> UserId:
    if not credentials:
        raise UnauthorizedError("Authentication token is missing.")
    return token_service.verify(credentials.credentials, TokenKind.ACCESS)


CurrentUserId = Annotated[UserId, Depends(get_current_user_id)]
