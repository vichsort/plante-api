from typing import Any

import jwt
from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.domain.exceptions import UnauthorizedError
from src.infrastructure.container import Container

_bearer = HTTPBearer(auto_error=False)

def _decode_access_token(token: str, secret: str, algorithm: str) -> Any:
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Access token expired.")
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid access token.")

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type.")

    return payload["sub"]

@inject
async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    secret_key: str = Depends(Provide[Container.settings.provided.secret_key]),
    algorithm: str = Depends(Provide[Container.settings.provided.jwt_algorithm]),
) -> Any:
    if not credentials:
        raise UnauthorizedError("Authentication token is missing.")
    return _decode_access_token(credentials.credentials, secret_key, algorithm)