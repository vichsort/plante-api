"""Errors the framework raises by itself also leave in the envelope, with a code of their own."""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.shared.api import register_exception_handlers


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/plants")
    async def plants() -> dict[str, str]:
        return {}

    @app.get("/unreadable")
    async def unreadable() -> None:
        raise HTTPException(status_code=400, detail="There was an error parsing the body")

    @app.get("/broken")
    async def broken() -> None:
        raise HTTPException(status_code=503, detail="internal detail")

    return TestClient(app)


def test_an_unknown_route_is_a_route_not_found(client: TestClient) -> None:
    # Act
    response = client.get("/nowhere")

    # Assert
    assert response.status_code == 404
    assert response.json()["ok"] is False
    assert response.json()["error"]["code"] == "PLANTE_4030_ROUTE_NOT_FOUND"


def test_a_wrong_method_is_a_method_not_allowed_and_keeps_the_allow_header(client: TestClient) -> None:
    # Act
    response = client.delete("/plants")

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (405, "PLANTE_4002_METHOD_NOT_ALLOWED")
    assert response.headers["allow"] == "GET"


def test_another_framework_client_error_is_an_invalid_request(client: TestClient) -> None:
    # Act
    response = client.get("/unreadable")

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (422, "PLANTE_4000_VALIDATION_ERROR")
    assert response.json()["error"]["message"] == "There was an error parsing the body"


def test_a_framework_server_error_hides_its_detail(client: TestClient) -> None:
    # Act
    response = client.get("/broken")

    # Assert
    assert (response.status_code, response.json()["error"]["code"]) == (500, "PLANTE_5000_INTERNAL_ERROR")
    assert "internal detail" not in response.text
