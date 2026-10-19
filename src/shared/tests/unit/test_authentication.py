"""`CurrentUserId`: o dono do access token, pelo verificador que a composição liga."""
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.shared.api import (
    CurrentUserId,
    install_authentication,
    register_exception_handlers,
)
from src.shared.domain import IAccessTokenVerifier, UnauthorizedError, UserId

ALICE = UserId(uuid4())


class _StubVerifier(IAccessTokenVerifier):
    """Aceita só o token "alice"."""

    def verify_access(self, token: str) -> UserId:
        if token != "alice":
            raise UnauthorizedError("Invalid access token.")
        return ALICE


def _app(verifier: IAccessTokenVerifier | None) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    if verifier is not None:
        install_authentication(app, lambda: verifier)

    @app.get("/me")
    async def me(user_id: CurrentUserId) -> dict[str, str]:
        return {"user_id": str(user_id)}

    return TestClient(app, raise_server_exceptions=True)


def test_valid_token_resolves_its_owner() -> None:
    # Arrange
    client = _app(_StubVerifier())

    # Act
    response = client.get("/me", headers={"Authorization": "Bearer alice"})

    # Assert
    assert response.json() == {"user_id": str(ALICE)}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer forged"}])
def test_missing_or_invalid_token_is_unauthorized(headers: dict[str, str]) -> None:
    # Arrange
    client = _app(_StubVerifier())

    # Act
    response = client.get("/me", headers=headers)

    # Assert
    assert response.status_code == 401
    assert response.json()["error"]["code"] == UnauthorizedError.code


def test_route_without_installed_authentication_fails_loudly() -> None:
    # Arrange: esquecer de ligar o verificador é erro de montagem, não 401 para o cliente
    client = _app(None)

    # Act & Assert
    with pytest.raises(RuntimeError, match="install_authentication"):
        client.get("/me", headers={"Authorization": "Bearer alice"})


def test_owner_of_is_none_for_a_token_that_does_not_count() -> None:
    # Arrange
    verifier = _StubVerifier()

    # Act
    owners = (verifier.owner_of("alice"), verifier.owner_of("forged"))

    # Assert
    assert owners == (ALICE, None)
