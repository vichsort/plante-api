import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.domain.use_cases.login_use_case import LoginResult
from src.domain.use_cases.refresh_token_use_case import RefreshResult
from tests.factories import make_user


def test_register_route_success(client: TestClient):
    mock_use_case = AsyncMock()
    user = make_user(email="integration@plante.org", is_verified=False)
    user_id = str(user.id)
    mock_use_case.execute.return_value = user

    with client.app.state.container.use_cases.register_user_use_case.override(mock_use_case):
        response = client.post("/auth/register", json={
            "email": "integration@plante.org",
            "password": "SecretPassword123",
            "country": "BR",
            "state": "SP",
        })

    assert response.status_code == 201
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["user_id"] == user_id
    assert payload["data"]["email"] == "integration@plante.org"
    assert payload["data"]["status"] == "pending_verification"
    assert "x-response-time-ms" in response.headers

def test_verify_email_route_success(client: TestClient):
    user_id = str(uuid.uuid4())
    mock_use_case = AsyncMock()

    with client.app.state.container.use_cases.verify_email_use_case.override(mock_use_case):
        response = client.post("/auth/verify-email", json={
            "user_id": user_id,
            "raw_code": "123456",
        })

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["message"] == "Email verified successfully."

def test_login_route_success(client: TestClient):
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = LoginResult(
        access_token="mocked_access_token",
        refresh_token="mocked_refresh_token",
    )

    with client.app.state.container.use_cases.login_use_case.override(mock_use_case):
        response = client.post("/auth/login", json={
            "email": "integration@plante.org",
            "password": "SecretPassword123",
        })

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["access_token"] == "mocked_access_token"
    assert payload["data"]["token_type"] == "bearer"
    assert "x-response-time-ms" in response.headers

def test_refresh_token_route_success(client: TestClient):
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = RefreshResult(
        access_token="new_access_token",
        refresh_token="new_refresh_token",
    )

    with client.app.state.container.use_cases.refresh_token_use_case.override(mock_use_case):
        response = client.post("/auth/refresh", json={
            "refresh_token": "valid_refresh_token",
        })

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["access_token"] == "new_access_token"

def test_logout_route_requires_auth(client: TestClient):
    response = client.post("/auth/logout")
    assert response.status_code == 401
    payload = response.json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "PLANTE_4006_UNAUTHORIZED"

def test_logout_route_success(client: TestClient, auth_headers: dict[str, str]):
    mock_use_case = AsyncMock()

    with client.app.state.container.use_cases.logout_use_case.override(mock_use_case):
        response = client.post("/auth/logout", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["message"] == "Logged out successfully."
