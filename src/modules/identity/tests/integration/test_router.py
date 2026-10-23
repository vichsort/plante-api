"""As rotas do módulo num app mínimo: só elas, o envelope e a autenticação do shared."""
from collections.abc import Iterator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.identity.api import router
from src.modules.identity.container import IdentityContainer
from src.modules.identity.domain.use_cases.login import LoginResult
from src.modules.identity.domain.use_cases.refresh_token import RefreshResult
from src.modules.identity.tests.fakes import make_user
from src.shared.api import install_authentication, register_exception_handlers
from src.shared.domain import IAccessTokenVerifier, UnauthorizedError, UserId

USER = UserId(uuid4())
AUTH = {"Authorization": "Bearer valid"}


class _Verifier(IAccessTokenVerifier):
    def verify_access(self, token: str) -> UserId:
        if token != "valid":
            raise UnauthorizedError("Invalid access token.")
        return USER


class _App:
    def __init__(self) -> None:
        self.container = IdentityContainer()
        self.container.wire(modules=["src.modules.identity.api.router"])
        app = FastAPI()
        register_exception_handlers(app)
        install_authentication(app, _Verifier)
        app.include_router(router)
        self.client = TestClient(app)

    def use_case(self, provider: providers.Provider[object], result: object = None) -> AsyncMock:
        mock = AsyncMock()
        mock.execute.return_value = result
        provider.override(providers.Object(mock))
        return mock


@pytest.fixture
def api() -> Iterator[_App]:
    app = _App()
    yield app
    app.container.unwire()


def test_register_returns_the_pending_account(api: _App) -> None:
    # Arrange
    user = make_user(email="integration@plante.org", is_verified=False)
    use_case = api.use_case(api.container.register_user_use_case, user)

    # Act
    response = api.client.post("/auth/register", json={
        "email": "integration@plante.org", "password": "SecretPassword123", "country": "BR", "state": "SP",
        "captcha_token": "widget-token",
    })

    # Assert
    assert response.status_code == 201
    assert response.json()["data"] == {"user_id": str(user.id), "email": "integration@plante.org", "status": "pending_verification"}
    dto = use_case.execute.call_args.args[0]
    assert (dto.captcha_token, dto.client_ip) == ("widget-token", "testclient")


@pytest.mark.parametrize(("path", "method", "location"), [
    ("/auth/register", "post", {"country": "BRA", "state": "SP"}),
    ("/auth/register", "post", {"country": "12", "state": "SP"}),
    ("/auth/register", "post", {"country": "BR", "state": " S "}),
    ("/profile/location", "patch", {"country": "BR", "state": "S" * 101}),
])
def test_an_invalid_location_is_refused_before_the_use_case(
    api: _App, path: str, method: str, location: dict[str, str],
) -> None:
    # Arrange: before, the value object raised ValueError and the request answered 500
    use_case = api.use_case(api.container.register_user_use_case)
    api.use_case(api.container.update_location_use_case)
    body = {"email": "integration@plante.org", "password": "SecretPassword123", **location}

    # Act
    response = api.client.request(method, path, json=body, headers=AUTH)

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (422, "PLANTE_4000_VALIDATION_ERROR")
    use_case.execute.assert_not_awaited()


def test_verify_email_confirms(api: _App) -> None:
    # Arrange
    api.use_case(api.container.verify_email_use_case)

    # Act
    response = api.client.post("/auth/verify-email", json={"user_id": str(uuid4()), "raw_code": "123456"})

    # Assert
    assert (response.status_code, response.json()["data"]["message"]) == (200, "Email verified successfully.")


def test_login_returns_the_tokens(api: _App) -> None:
    # Arrange
    api.use_case(api.container.login_use_case, LoginResult(access_token="access", refresh_token="refresh"))

    # Act
    response = api.client.post("/auth/login", json={"email": "integration@plante.org", "password": "SecretPassword123"})

    # Assert
    assert response.status_code == 200
    assert response.json()["data"] == {"access_token": "access", "refresh_token": "refresh", "token_type": "bearer"}


def test_refresh_returns_new_tokens(api: _App) -> None:
    # Arrange
    api.use_case(api.container.refresh_token_use_case, RefreshResult(access_token="new_access", refresh_token="new_refresh"))

    # Act
    response = api.client.post("/auth/refresh", json={"refresh_token": "valid_refresh_token"})

    # Assert
    assert (response.status_code, response.json()["data"]["access_token"]) == (200, "new_access")


def test_logout_requires_authentication(api: _App) -> None:
    # Act
    response = api.client.post("/auth/logout")

    # Assert
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "PLANTE_4010_UNAUTHORIZED"


def test_logout_revokes_the_callers_session(api: _App) -> None:
    # Arrange
    use_case = api.use_case(api.container.logout_use_case)

    # Act
    response = api.client.post("/auth/logout", headers=AUTH)

    # Assert
    assert (response.status_code, response.json()["data"]["message"]) == (200, "Logged out successfully.")
    use_case.execute.assert_awaited_once_with(user_id=USER)


@pytest.mark.parametrize("path, body, message", [
    ("/profile/email", {"current_password": "Old123", "new_email": "new_email@plante.org"}, "Verification code sent to new email."),
    ("/profile/password", {"current_password": "Old123", "new_password": "NewPassword456"}, "Password updated successfully."),
    ("/profile/location", {"country": "BR", "state": "RJ"}, "Location updated successfully."),
])
def test_profile_changes_are_confirmed(api: _App, path: str, body: dict[str, str], message: str) -> None:
    # Arrange
    use_case_for = {
        "/profile/email": api.container.change_email_use_case,
        "/profile/password": api.container.change_password_use_case,
        "/profile/location": api.container.update_location_use_case,
    }
    use_case = api.use_case(use_case_for[path])

    # Act
    response = api.client.patch(path, json=body, headers=AUTH)

    # Assert
    assert (response.status_code, response.json()["data"]["message"]) == (200, message)
    assert use_case.execute.call_args.args[0].user_id == USER


def test_delete_account_takes_the_password_in_the_body(api: _App) -> None:
    # Arrange
    use_case = api.use_case(api.container.delete_account_use_case)

    # Act
    response = api.client.request("DELETE", "/profile", json={"password": "SecretPassword123"}, headers=AUTH)

    # Assert
    assert (response.status_code, response.json()["data"]["message"]) == (200, "Account deleted.")
    dto = use_case.execute.call_args.args[0]
    assert (dto.user_id, dto.password) == (USER, "SecretPassword123")


def test_delete_account_without_the_password_is_refused(api: _App) -> None:
    # Arrange
    use_case = api.use_case(api.container.delete_account_use_case)

    # Act
    response = api.client.request("DELETE", "/profile", headers=AUTH)

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (422, "PLANTE_4000_VALIDATION_ERROR")
    use_case.execute.assert_not_awaited()
