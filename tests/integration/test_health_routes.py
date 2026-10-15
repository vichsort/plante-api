import io
import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.domain.use_cases.diagnose_health_use_case import DiagnoseHealthOutput
from tests.factories import make_health_record, make_health_sample


def test_diagnose_health_route_success(client: TestClient, auth_headers: dict[str, str]):
    user_plant_id = str(uuid.uuid4())
    record = make_health_record()
    health_record_id = str(record.id)

    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = DiagnoseHealthOutput(
        record=record,
        similar_images_urls=("https://storage.plante.org/similar1.jpg",),
    )

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
    sample = make_health_sample()
    health_record_id = str(sample.health_record_id)

    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = sample

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
    record = make_health_record()
    health_record_id = str(record.id)
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = [record]

    with client.app.state.container.use_cases.get_health_history_use_case.override(mock_use_case):
        response = client.get(f"/diagnose/history/{user_plant_id}", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["data"]) == 1
    assert payload["data"][0]["health_record_id"] == health_record_id
    assert payload["data"][0]["severity"] == "moderate"
