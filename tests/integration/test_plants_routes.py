from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.domain.ports.user_plant_repository import PlantDetails
from tests.factories import make_species, make_user_plant


def test_get_plant_details_route_success(client: TestClient, auth_headers: dict[str, str]):
    plant = make_user_plant()
    plant.nickname = "Clotilde"
    user_plant_id = str(plant.id)

    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = PlantDetails(plant=plant, species=make_species())

    with client.app.state.container.use_cases.get_plant_details_use_case.override(mock_use_case):
        response = client.get(f"/plants/{user_plant_id}", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["id"] == user_plant_id
    assert payload["data"]["nickname"] == "Clotilde"
    assert payload["data"]["species_info"]["family"] == "Araceae"
