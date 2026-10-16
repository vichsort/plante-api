"""
Autenticação das rotas: `CurrentUserId` resolve o dono do access token do header `Authorization`.
O kernel não sabe emitir tokens; a composição liga quem sabe (`install_authentication`).
"""
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.shared.domain import IAccessTokenVerifier, UnauthorizedError, UserId

_bearer = HTTPBearer(auto_error=False)
_STATE_KEY = "access_token_verifier"


def install_authentication(app: FastAPI, verifier: Callable[[], IAccessTokenVerifier]) -> None:
    """
    Liga o verificador às rotas do app. Recebe a fábrica (o provider do container), não a
    instância, para um override no container valer também aqui.
    """
    setattr(app.state, _STATE_KEY, verifier)


def _verifier(request: Request) -> IAccessTokenVerifier:
    factory = getattr(request.app.state, _STATE_KEY, None)
    verifier = factory() if callable(factory) else None
    if not isinstance(verifier, IAccessTokenVerifier):
        raise RuntimeError("Authentication is not installed: call install_authentication(app, verifier).")
    return verifier


async def current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    verifier: Annotated[IAccessTokenVerifier, Depends(_verifier)],
) -> UserId:
    if not credentials:
        raise UnauthorizedError("Authentication token is missing.")
    return verifier.verify_access(credentials.credentials)


CurrentUserId = Annotated[UserId, Depends(current_user_id)]
