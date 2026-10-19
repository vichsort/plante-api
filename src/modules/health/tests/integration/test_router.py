"""As rotas do módulo num app mínimo: só elas, o envelope e a autenticação do shared."""
from collections.abc import Iterator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.garden import PlantNotFoundError
from src.modules.health.api import router
from src.modules.health.container import HealthContainer
from src.modules.health.domain.exceptions import HealthRecordNotFoundError
from src.modules.health.domain.use_cases.diagnose import DiagnoseHealthOutput
from src.modules.health.tests.fakes import make_health_record
from src.modules.training import FeedbackVerdict
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
        self.container = HealthContainer()
        self.container.wire(modules=["src.modules.health.api.router"])
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


def test_diagnose_returns_the_record_and_the_reference_images(api: _App) -> None:
    # Arrange
    record = make_health_record(user_id=USER)
    use_case = api.use_case(
        api.container.diagnose_use_case,
        DiagnoseHealthOutput(record=record, similar_images_urls=("https://storage.plante.org/similar1.jpg",)),
    )

    # Act
    response = api.client.post(
        "/diagnose",
        files={"image": ("leaf.jpg", b"leaf bytes", "image/jpeg")},
        data={"user_plant_id": str(record.user_plant_id), "latitude": "-23.5", "longitude": "-46.6"},
        headers=AUTH,
    )

    # Assert
    assert response.status_code == 200
    data = response.json()["data"]
    assert (data["health_record_id"], data["severity"], data["is_healthy"]) == (str(record.id), "moderate", False)
    assert data["similar_images_urls"] == ["https://storage.plante.org/similar1.jpg"]
    dto = use_case.execute.call_args.args[0]
    assert (dto.user_id, dto.user_plant_id, dto.image_bytes, dto.latitude, dto.longitude) == (
        USER, record.user_plant_id, b"leaf bytes", -23.5, -46.6,
    )


def test_diagnose_rejects_coordinates_out_of_range(api: _App) -> None:
    # Arrange
    use_case = api.use_case(api.container.diagnose_use_case)

    # Act
    response = api.client.post(
        "/diagnose",
        files={"image": ("leaf.jpg", b"leaf bytes", "image/jpeg")},
        data={"user_plant_id": str(uuid4()), "latitude": "91"},
        headers=AUTH,
    )

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (422, "PLANTE_4220_VALIDATION_ERROR")
    use_case.execute.assert_not_called()


def test_diagnosing_a_missing_plant_is_not_found(api: _App) -> None:
    # Arrange
    plant_id = uuid4()
    api.use_case(api.container.diagnose_use_case).execute.side_effect = PlantNotFoundError(plant_id)

    # Act
    response = api.client.post(
        "/diagnose", files={"image": ("leaf.jpg", b"x", "image/jpeg")}, data={"user_plant_id": str(plant_id)}, headers=AUTH,
    )

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (404, "PLANTE_4001_PLANT_NOT_FOUND")


def test_feedback_passes_the_verdict(api: _App) -> None:
    # Arrange
    record_id = uuid4()
    use_case = api.use_case(api.container.give_feedback_use_case)

    # Act
    response = api.client.post(f"/diagnose/{record_id}/feedback", json={"verdict": "correct"}, headers=AUTH)

    # Assert
    assert response.status_code == 200
    dto = use_case.execute.call_args.args[0]
    assert (dto.user_id, dto.health_record_id, dto.verdict) == (USER, record_id, FeedbackVerdict.CORRECT)


def test_feedback_on_a_missing_diagnosis_is_not_found(api: _App) -> None:
    # Arrange
    record_id = uuid4()
    api.use_case(api.container.give_feedback_use_case).execute.side_effect = HealthRecordNotFoundError(record_id)

    # Act
    response = api.client.post(f"/diagnose/{record_id}/feedback", json={"verdict": "wrong"}, headers=AUTH)

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (404, "PLANTE_4017_HEALTH_RECORD_NOT_FOUND")


def test_history_lists_the_diagnoses(api: _App) -> None:
    # Arrange
    record = make_health_record(user_id=USER)
    use_case = api.use_case(api.container.get_history_use_case, [record])

    # Act
    response = api.client.get(f"/diagnose/history/{record.user_plant_id}?limit=5", headers=AUTH)

    # Assert
    assert response.status_code == 200
    (item,) = response.json()["data"]
    assert (item["health_record_id"], item["severity"]) == (str(record.id), "moderate")
    dto = use_case.execute.call_args.args[0]
    assert (dto.user_id, dto.user_plant_id, dto.limit) == (USER, record.user_plant_id, 5)


def test_diagnose_requires_authentication(api: _App) -> None:
    # Act
    response = api.client.get(f"/diagnose/history/{uuid4()}")

    # Assert
    assert response.status_code == 401
