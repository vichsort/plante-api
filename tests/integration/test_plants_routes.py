import uuid
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


def test_get_plant_details_route_success(client: TestClient, auth_headers: dict[str, str]):
    user_plant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = {
        "id": user_plant_id,
        "user_id": user_id,
        "scientific_name": "Monstera deliciosa",
        "nickname": "Clotilde",
        "display_name": "Clotilde",
        "primary_image_url": "https://storage.plante.org/img.jpg",
        "identification_confidence": 0.95,
        "identification_source": "consensus",
        "status": "identified",
        "added_at": "2026-08-01T10:00:00+00:00",
        "last_watered_at": "2026-08-08T10:00:00+00:00",
        "needs_watering": False,
        "watering_streak": 2,
        "care_schedule": {
            "care_type": "water",
            "interval_days": 2,
            "is_active": True,
            "next_due_at": "2026-08-10T10:00:00+00:00",
        },
        "species_info": {
            "family": "Araceae",
            "genus": "Monstera",
            "common_names": ["Costela-de-Adão"],
            "is_edible": False,
            "water_frequency_per_week": 2,
            "light_requirement": "indirect",
            "soil_type": "well_draining",
            "habitat": "Tropical rainforests",
        },
    }

    with client.app.state.container.use_cases.get_plant_details_use_case.override(mock_use_case):
        response = client.get(f"/plants/{user_plant_id}", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["id"] == user_plant_id
    assert payload["data"]["nickname"] == "Clotilde"
    assert payload["data"]["species_info"]["family"] == "Araceae"
