from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from tests.factories import NOW, make_user_plant


def test_get_garden_route_success(client: TestClient, auth_headers: dict[str, str]):
    plant = make_user_plant()
    plant.nickname = "Clotilde"
    user_plant_id = str(plant.id)
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = [plant]

    with client.app.state.container.use_cases.get_user_garden_use_case.override(mock_use_case):
        response = client.get("/garden", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert len(payload["data"]) == 1
    assert payload["data"][0]["id"] == user_plant_id
    assert payload["data"][0]["nickname"] == "Clotilde"
    assert payload["data"][0]["display_name"] == "Clotilde"
    assert "x-response-time-ms" in response.headers

def test_water_plant_route_success(client: TestClient, auth_headers: dict[str, str]):
    plant = make_user_plant()
    plant.water(NOW)
    user_plant_id = str(plant.id)
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = plant

    with client.app.state.container.use_cases.water_plant_use_case.override(mock_use_case):
        response = client.post(f"/garden/{user_plant_id}/water", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["user_plant_id"] == user_plant_id
    assert payload["data"]["current_streak"] == 1
    assert payload["data"]["last_watered_at"] == "2026-10-15T12:00:00Z"


def test_add_plant_to_garden_route_creates_plant_from_identification(client: TestClient, auth_headers: dict[str, str]):
    plant = make_user_plant()
    mock_use_case = AsyncMock()
    mock_use_case.execute.return_value = plant

    with client.app.state.container.use_cases.add_plant_to_garden_use_case.override(mock_use_case):
        response = client.post(
            "/garden",
            json={"identification_id": str(plant.identification_id), "nickname": "Clotilde"},
            headers=auth_headers,
        )

    assert response.status_code == 201
    assert response.json()["data"]["id"] == str(plant.id)
    dto = mock_use_case.execute.call_args.args[0]
    assert dto.identification_id == plant.identification_id
    assert dto.nickname == "Clotilde"


def test_delete_plant_route_needs_no_body(client: TestClient, auth_headers: dict[str, str]):
    plant = make_user_plant()
    mock_use_case = AsyncMock()

    with client.app.state.container.use_cases.delete_user_plant_use_case.override(mock_use_case):
        response = client.delete(f"/garden/{plant.id}", headers=auth_headers)

    assert response.status_code == 200
    assert mock_use_case.execute.call_args.args[0].user_plant_id == plant.id
