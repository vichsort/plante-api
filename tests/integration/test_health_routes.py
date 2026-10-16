import io
import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.domain.use_cases.diagnose_health_use_case import DiagnoseHealthOutput
from src.modules.training import FeedbackVerdict
from tests.factories import make_health_record


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

def test_health_feedback_route(client: TestClient, auth_headers: dict[str, str]):
    health_record_id = uuid.uuid4()
    mock_use_case = AsyncMock()

    with client.app.state.container.use_cases.give_health_feedback_use_case.override(mock_use_case):
        response = client.post(
            f"/diagnose/{health_record_id}/feedback",
            json={"verdict": "correct"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    dto = mock_use_case.execute.call_args.args[0]
    assert dto.health_record_id == health_record_id
    assert dto.verdict == FeedbackVerdict.CORRECT

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
