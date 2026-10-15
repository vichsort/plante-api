import io
import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.domain.entities.plant_identification_sample import SampleStatus
from src.domain.use_cases.identify_plant_use_case import IdentifyPlantOutput
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.domain.value_objects.ids import IdentificationSampleId, UserPlantId
from tests.factories import make_identification_sample


def test_identify_plant_route_success(client: TestClient, auth_headers: dict[str, str]):
    user_plant_id = uuid.uuid4()
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = IdentifyPlantOutput(
        user_plant_id=UserPlantId(user_plant_id),
        sample_id=IdentificationSampleId(uuid.uuid4()),
        scientific_name="Monstera deliciosa",
        confidence=ConfidenceScore(0.95),
        image_url="https://storage.plante.org/samples/123.jpg",
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
    assert payload["data"]["scientific_name"] == "Monstera deliciosa"
    assert payload["data"]["user_plant_id"] == str(user_plant_id)
    assert payload["data"]["confidence"] == "95.0%"

def test_confirm_plant_identification_route_success(client: TestClient, auth_headers: dict[str, str]):
    sample = make_identification_sample(status=SampleStatus.CONFIRMED)
    sample_id = str(sample.id)

    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = sample

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
