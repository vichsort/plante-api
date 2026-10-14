import io
import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


def test_diagnose_health_route_success(client: TestClient, auth_headers: dict[str, str]):
    user_plant_id = str(uuid.uuid4())
    health_record_id = str(uuid.uuid4())

    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = {
        "health_record_id": health_record_id,
        "severity": "moderate",
        "vitality_score": 0.70,
        "is_healthy": False,
        "issues_detected": ["leaf_spots"],
        "treatment_plan": ["isolate_plant", "apply_fungicide"],
        "recovery_estimate_days": 14,
        "image_key": "health/sample.jpg",
        "similar_images_urls": ["https://storage.plante.org/similar1.jpg"],
    }

    fake_file = ("leaf.jpg", io.BytesIO(b"fake leaf image bytes"), "image/jpeg")

    with client.app.state.container.use_cases.diagnose_health_use_case.override(mock_use_case):
        response = client.post(
            "/diagnose",
            files={"image": fake_file},
            data={"user_plant_id": user_plant_id},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["health_record_id"] == health_record_id
    assert payload["data"]["severity"] == "moderate"

def test_confirm_health_diagnosis_route_success(client: TestClient, auth_headers: dict[str, str]):
    sample_id = str(uuid.uuid4())
    health_record_id = str(uuid.uuid4())

    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = {
        "sample_id": sample_id,
        "health_record_id": health_record_id,
        "scientific_name": "Monstera deliciosa",
        "status": "confirmed",
        "confirmed_at": "2026-08-10T16:00:00+00:00",
    }

    with client.app.state.container.use_cases.confirm_health_diagnosis.override(mock_use_case):
        response = client.post(
            "/diagnose/confirm",
            json={"health_record_id": health_record_id},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["health_record_id"] == health_record_id
    assert payload["data"]["status"] == "confirmed"

def test_health_history_route_success(client: TestClient, auth_headers: dict[str, str]):
    user_plant_id = str(uuid.uuid4())
    health_record_id = str(uuid.uuid4())
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = [
        {
            "health_record_id": health_record_id,
            "diagnosed_at": "2026-08-05T12:00:00+00:00",
            "severity": "low",
            "vitality_score": 0.85,
            "is_healthy": False,
            "issues_detected": ["mild_yellowing"],
            "treatment_plan": ["reduce_watering"],
            "recovery_estimate_days": 7,
            "image_key": "health/123.jpg",
        }
    ]

    with client.app.state.container.use_cases.get_health_history_use_case.override(mock_use_case):
        response = client.get(f"/diagnose/history/{user_plant_id}", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["data"]) == 1
    assert payload["data"][0]["health_record_id"] == health_record_id
    assert payload["data"][0]["severity"] == "low"
