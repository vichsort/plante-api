import io
import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


def test_identify_plant_route_success(client: TestClient, auth_headers: dict[str, str]):
    user_plant_id = str(uuid.uuid4())
    sample_id = str(uuid.uuid4())

    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = {
        "user_plant_id": user_plant_id,
        "sample_id": sample_id,
        "scientific_name": "Monstera deliciosa",
        "confidence": "95%",
        "image_url": "https://storage.plante.org/samples/123.jpg",
        "needs_human_review": False,
    }

    fake_file = ("plant.jpg", io.BytesIO(b"fake image bytes"), "image/jpeg")

    with client.app.state.container.use_cases.identify_plant_use_case.override(mock_use_case):
        response = client.post(
            "/identify",
            files={"image": fake_file},
            data={"latitude": "-23.5505", "longitude": "-46.6333"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["scientific_name"] == "Monstera deliciosa"
    assert payload["data"]["user_plant_id"] == user_plant_id

def test_confirm_plant_identification_route_success(client: TestClient, auth_headers: dict[str, str]):
    sample_id = str(uuid.uuid4())

    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = {
        "sample_id": sample_id,
        "scientific_name": "Monstera deliciosa",
        "status": "confirmed",
        "confirmed_at": "2026-08-10T16:00:00+00:00",
    }

    with client.app.state.container.use_cases.confirm_plant_identification.override(mock_use_case):
        response = client.post(
            "/identify/confirm",
            json={"sample_id": sample_id},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["sample_id"] == sample_id
    assert payload["data"]["status"] == "confirmed"
