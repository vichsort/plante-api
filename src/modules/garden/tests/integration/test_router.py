"""As rotas do módulo num app mínimo: só elas, o envelope e a autenticação do shared."""
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.catalog import PlantSpecies
from src.modules.garden.api import router
from src.modules.garden.container import GardenContainer
from src.modules.garden.domain.entities.user_plant import GardenPlant
from src.modules.garden.domain.exceptions import (
    PlantNotFoundError,
    PlantNotReadyForWateringError,
)
from src.modules.garden.domain.use_cases.get_plant_details import PlantDetailsOutput
from src.modules.garden.tests.fakes import CALENDAR, make_user_plant
from src.shared.api import install_authentication, register_exception_handlers
from src.shared.domain import IAccessTokenVerifier, UnauthorizedError, UserId

USER = UserId(uuid4())
AUTH = {"Authorization": "Bearer valid"}


class _Verifier(IAccessTokenVerifier):
    def verify_access(self, token: str) -> UserId:
        if token != "valid":
            raise UnauthorizedError("Invalid access token.")
        return USER


class _App:
    def __init__(self) -> None:
        self.container = GardenContainer()
        self.container.wire(modules=["src.modules.garden.api.router"])
        app = FastAPI()
        register_exception_handlers(app)
        install_authentication(app, _Verifier)
        app.include_router(router)
        self.client = TestClient(app)

    def use_case(self, provider: providers.Provider[object], result: object = None) -> AsyncMock:
        mock = AsyncMock()
        mock.execute.return_value = result
        provider.override(providers.Object(mock))
        return mock


@pytest.fixture
def api() -> Iterator[_App]:
    app = _App()
    yield app
    app.container.unwire()


def test_garden_lists_the_plants(api: _App) -> None:
    # Arrange
    plant = make_user_plant(user_id=USER)
    plant.nickname = "Clotilde"
    use_case = api.use_case(api.container.get_garden_use_case, [GardenPlant(plant=plant, needs_watering=True)])

    # Act
    response = api.client.get("/garden", headers=AUTH)

    # Assert
    assert response.status_code == 200
    (item,) = response.json()["data"]
    assert (item["id"], item["display_name"], item["needs_watering"]) == (str(plant.id), "Clotilde", True)
    assert use_case.execute.call_args.args[0].user_id == USER


def test_add_creates_the_plant_from_the_identification(api: _App) -> None:
    # Arrange
    plant = make_user_plant(user_id=USER)
    use_case = api.use_case(api.container.add_plant_use_case, GardenPlant(plant=plant, needs_watering=False))

    # Act
    response = api.client.post(
        "/garden", json={"identification_id": str(plant.identification_id), "nickname": "Clotilde"}, headers=AUTH,
    )

    # Assert
    assert (response.status_code, response.json()["data"]["id"]) == (201, str(plant.id))
    dto = use_case.execute.call_args.args[0]
    assert (dto.user_id, dto.identification_id, dto.nickname) == (USER, plant.identification_id, "Clotilde")


def test_watering_returns_the_next_due_day_and_the_streak(api: _App) -> None:
    # Arrange
    plant = make_user_plant(user_id=USER)
    plant.water(datetime(2026, 10, 15, 12, 0, tzinfo=UTC), CALENDAR)
    api.use_case(api.container.water_plant_use_case, plant)

    # Act
    response = api.client.post(f"/garden/{plant.id}/water", headers=AUTH)

    # Assert
    assert response.status_code == 200
    assert response.json()["data"] == {
        "user_plant_id": str(plant.id),
        "last_watered_at": "2026-10-15T12:00:00Z",
        "next_due_on": "2026-10-22",
        "current_streak": 1,
    }


def test_watering_too_early_is_refused(api: _App) -> None:
    # Arrange
    api.use_case(api.container.water_plant_use_case).execute.side_effect = PlantNotReadyForWateringError("22/10/2026")

    # Act
    response = api.client.post(f"/garden/{uuid4()}/water", headers=AUTH)

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (400, "PLANTE_4016_NOT_READY_FOR_WATERING")


def test_delete_needs_no_body(api: _App) -> None:
    # Arrange
    plant_id = uuid4()
    use_case = api.use_case(api.container.delete_plant_use_case)

    # Act
    response = api.client.delete(f"/garden/{plant_id}", headers=AUTH)

    # Assert
    assert response.status_code == 200
    assert use_case.execute.call_args.args[0].user_plant_id == plant_id


def test_plant_details_include_the_species(api: _App) -> None:
    # Arrange
    plant = make_user_plant(user_id=USER)
    species = PlantSpecies.create_skeleton("Monstera deliciosa", family="Araceae")
    api.use_case(api.container.get_plant_details_use_case, PlantDetailsOutput(plant=plant, species=species, needs_watering=False))

    # Act
    response = api.client.get(f"/plants/{plant.id}", headers=AUTH)

    # Assert
    assert response.status_code == 200
    data = response.json()["data"]
    assert (data["id"], data["species_info"]["family"], data["care_schedule"]["interval_days"]) == (str(plant.id), "Araceae", 7)


def test_details_of_a_missing_plant_are_not_found(api: _App) -> None:
    # Arrange
    plant_id = uuid4()
    api.use_case(api.container.get_plant_details_use_case).execute.side_effect = PlantNotFoundError(plant_id)

    # Act
    response = api.client.get(f"/plants/{plant_id}", headers=AUTH)

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (404, "PLANTE_4001_PLANT_NOT_FOUND")


def test_garden_requires_authentication(api: _App) -> None:
    # Act
    response = api.client.get("/garden")

    # Assert
    assert response.status_code == 401
