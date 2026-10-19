"""As rotas do módulo num app mínimo: só elas, o envelope e a autenticação do shared."""
import io
from collections.abc import Iterator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.identification.api import router
from src.modules.identification.container import IdentificationContainer
from src.modules.identification.domain.exceptions import IdentificationNotFoundError
from src.modules.identification.domain.use_cases.identify_plant import (
    IdentifyPlantOutput,
)
from src.modules.identification.domain.value_objects.confidence_score import (
    ConfidenceScore,
)
from src.modules.identification.domain.value_objects.ids import IdentificationId
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
        self.container = IdentificationContainer()
        self.container.wire(modules=["src.modules.identification.api.router"])
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


def _photo() -> dict[str, tuple[str, io.BytesIO, str]]:
    return {"image": ("plant.jpg", io.BytesIO(b"fake image bytes"), "image/jpeg")}


def test_identify_returns_the_identification(api: _App) -> None:
    # Arrange
    identification_id = IdentificationId(uuid4())
    use_case = api.use_case(api.container.identify_plant_use_case, IdentifyPlantOutput(
        identification_id=identification_id,
        scientific_name="Monstera deliciosa",
        confidence=ConfidenceScore(0.95),
        image_url="identifications/monstera/123.jpg",
        needs_human_review=False,
    ))

    # Act
    response = api.client.post("/identify", files=_photo(), data={"latitude": "-23.5505", "longitude": "-46.6333"}, headers=AUTH)

    # Assert
    assert response.status_code == 200
    assert response.json()["data"] == {
        "identification_id": str(identification_id),
        "scientific_name": "Monstera deliciosa",
        "confidence": "95.0%",
        "image_url": "identifications/monstera/123.jpg",
        "needs_human_review": False,
    }
    dto = use_case.execute.call_args.args[0]
    assert (dto.user_id, dto.image_bytes, dto.latitude, dto.longitude) == (USER, b"fake image bytes", -23.5505, -46.6333)


def test_identify_rejects_out_of_range_coordinates(api: _App) -> None:
    # Arrange
    use_case = api.use_case(api.container.identify_plant_use_case)

    # Act
    response = api.client.post("/identify", files=_photo(), data={"latitude": "123"}, headers=AUTH)

    # Assert
    assert response.status_code == 422
    use_case.execute.assert_not_called()


def test_identify_requires_authentication(api: _App) -> None:
    # Act
    response = api.client.post("/identify", files=_photo())

    # Assert
    assert response.status_code == 401


def test_feedback_is_recorded(api: _App) -> None:
    # Arrange
    identification_id = uuid4()
    use_case = api.use_case(api.container.give_feedback_use_case)

    # Act
    response = api.client.post(
        f"/identify/{identification_id}/feedback",
        json={"verdict": "wrong", "suggested_name": "Monstera adansonii"},
        headers=AUTH,
    )

    # Assert
    assert (response.status_code, response.json()["data"]["message"]) == (200, "Feedback recorded.")
    dto = use_case.execute.call_args.args[0]
    assert (dto.user_id, dto.identification_id) == (USER, identification_id)
    assert (dto.verdict, dto.suggested_name) == (FeedbackVerdict.WRONG, "Monstera adansonii")


def test_feedback_on_unknown_identification_is_not_found(api: _App) -> None:
    # Arrange
    identification_id = uuid4()
    api.use_case(api.container.give_feedback_use_case).execute.side_effect = IdentificationNotFoundError(identification_id)

    # Act
    response = api.client.post(f"/identify/{identification_id}/feedback", json={"verdict": "correct"}, headers=AUTH)

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (404, "PLANTE_4012_IDENTIFICATION_NOT_FOUND")


def test_feedback_rejects_an_unknown_verdict(api: _App) -> None:
    # Act
    response = api.client.post(f"/identify/{uuid4()}/feedback", json={"verdict": "maybe"}, headers=AUTH)

    # Assert
    assert response.status_code == 422
