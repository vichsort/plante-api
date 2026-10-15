import io
import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.domain.entities.training import FeedbackVerdict
from src.domain.use_cases.identify_plant_use_case import IdentifyPlantOutput
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.domain.value_objects.ids import IdentificationId


def test_identify_plant_route_success(client: TestClient, auth_headers: dict[str, str]):
    identification_id = uuid.uuid4()
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = IdentifyPlantOutput(
        identification_id=IdentificationId(identification_id),
        scientific_name="Monstera deliciosa",
        confidence=ConfidenceScore(0.95),
        image_url="identifications/monstera/123.jpg",
        needs_human_review=False,
    )

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
    assert payload["data"]["identification_id"] == str(identification_id)
    assert payload["data"]["scientific_name"] == "Monstera deliciosa"
    assert payload["data"]["confidence"] == "95.0%"
    dto = mock_use_case.execute.call_args.args[0]
    assert (dto.latitude, dto.longitude) == (-23.5505, -46.6333)


def test_identify_rejects_out_of_range_coordinates(client: TestClient, auth_headers: dict[str, str]):
    fake_file = ("plant.jpg", io.BytesIO(b"fake image bytes"), "image/jpeg")

    response = client.post("/identify", files={"image": fake_file}, data={"latitude": "123"}, headers=auth_headers)

    assert response.status_code == 422


def test_identification_feedback_route(client: TestClient, auth_headers: dict[str, str]):
    identification_id = uuid.uuid4()
    mock_use_case = AsyncMock()

    with client.app.state.container.use_cases.give_identification_feedback_use_case.override(mock_use_case):
        response = client.post(
            f"/identify/{identification_id}/feedback",
            json={"verdict": "wrong", "suggested_name": "Monstera adansonii"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    dto = mock_use_case.execute.call_args.args[0]
    assert dto.identification_id == identification_id
    assert dto.verdict == FeedbackVerdict.WRONG
    assert dto.suggested_name == "Monstera adansonii"


def test_identification_feedback_rejects_unknown_verdict(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(f"/identify/{uuid.uuid4()}/feedback", json={"verdict": "maybe"}, headers=auth_headers)

    assert response.status_code == 422
