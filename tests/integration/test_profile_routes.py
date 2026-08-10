import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


def test_change_email_route_success(client: TestClient, auth_headers: dict[str, str]):
    mock_use_case = AsyncMock()

    with client.app.state.container.use_cases.change_email_use_case.override(mock_use_case):
        response = client.patch(
            "/profile/email",
            json={"current_password": "OldPassword123", "new_email": "new_email@plante.org"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["message"] == "Verification code sent to new email."

def test_change_password_route_success(client: TestClient, auth_headers: dict[str, str]):
    mock_use_case = AsyncMock()

    with client.app.state.container.use_cases.change_password_use_case.override(mock_use_case):
        response = client.patch(
            "/profile/password",
            json={"current_password": "OldPassword123", "new_password": "NewPassword456"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["message"] == "Password updated successfully."

def test_update_location_route_success(client: TestClient, auth_headers: dict[str, str]):
    mock_use_case = AsyncMock()

    with client.app.state.container.use_cases.update_location_fallback_use_case.override(mock_use_case):
        response = client.patch(
            "/profile/location",
            json={"country": "BR", "state": "RJ"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["message"] == "Location updated successfully."

def test_upgrade_subscription_route_success(client: TestClient, auth_headers: dict[str, str]):
    user_id = str(uuid.uuid4())
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = {
        "user_id": user_id,
        "subscription": "PRO",
        "expires_at": "2027-08-10T16:00:00+00:00",
    }

    with client.app.state.container.use_cases.upgrade_subscription_use_case.override(mock_use_case):
        response = client.post(
            "/profile/subscription/upgrade",
            json={"plan_duration_days": 365},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["subscription"] == "PRO"

def test_list_achievements_route_success(client: TestClient, auth_headers: dict[str, str]):
    achievement_id = str(uuid.uuid4())
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = [
        {
            "id": achievement_id,
            "badge_code": "FIRST_PLANT_ADDED",
            "unlocked_at": "2026-08-01T12:00:00+00:00",
        }
    ]

    with client.app.state.container.use_cases.list_user_achievements_use_case.override(mock_use_case):
        response = client.get("/profile/achievements", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["data"]) == 1
    assert payload["data"][0]["badge_code"] == "FIRST_PLANT_ADDED"
