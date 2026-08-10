import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


def test_get_garden_route_success(client: TestClient, auth_headers: dict[str, str]):
    user_plant_id = str(uuid.uuid4())
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = [
        {
            "id": user_plant_id,
            "scientific_name": "Monstera deliciosa",
            "nickname": "Clotilde",
            "display_name": "Clotilde",
            "primary_image_url": "https://storage.plante.org/img.jpg",
            "last_watered_at": "2026-08-01T10:00:00+00:00",
            "next_due_at": "2026-08-03T10:00:00+00:00",
            "needs_watering": True,
            "streak_count": 3,
        }
    ]

    with client.app.state.container.use_cases.get_user_garden_use_case.override(mock_use_case):
        response = client.get("/garden", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["data"]) == 1
    assert payload["data"][0]["id"] == user_plant_id
    assert payload["data"][0]["nickname"] == "Clotilde"
    assert "x-response-time-ms" in response.headers

def test_water_plant_route_success(client: TestClient, auth_headers: dict[str, str]):
    user_plant_id = str(uuid.uuid4())
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = {
        "user_plant_id": user_plant_id,
        "last_watered_at": "2026-08-10T16:00:00+00:00",
        "next_due_at": "2026-08-12T16:00:00+00:00",
        "current_streak": 4,
    }

    with client.app.state.container.use_cases.water_plant_use_case.override(mock_use_case):
        response = client.post(f"/garden/{user_plant_id}/water", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["user_plant_id"] == user_plant_id
    assert payload["data"]["current_streak"] == 4
