from fastapi.testclient import TestClient

from src.api.openapi import error_responses
from src.domain.exceptions import (
    PlantLimitExceededError,
    PlantNotFoundError,
    SampleNotFoundError,
)


def test_error_responses_groups_examples_by_status():
    responses = error_responses(PlantNotFoundError, SampleNotFoundError, PlantLimitExceededError)

    not_found = responses[404]["content"]["application/json"]["examples"]
    assert set(not_found) == {PlantNotFoundError.code, SampleNotFoundError.code}
    assert not_found[PlantNotFoundError.code]["value"]["error"]["code"] == PlantNotFoundError.code
    # Exceção com argumento obrigatório usa a docstring como mensagem de exemplo
    forbidden = responses[PlantLimitExceededError.status_code]["content"]["application/json"]["examples"]
    assert forbidden[PlantLimitExceededError.code]["value"]["error"]["message"]


def test_openapi_documents_domain_and_common_errors(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    water = paths["/garden/{user_plant_id}/water"]["post"]["responses"]
    assert set(water) == {"200", "400", "401", "403", "404", "422", "429", "500"}
    examples_429 = water["429"]["content"]["application/json"]["examples"]
    assert "PLANTE_4029_RATE_LIMIT_EXCEEDED" in examples_429

    login = paths["/auth/login"]["post"]["responses"]
    assert "PLANTE_4006_UNAUTHORIZED" in login["401"]["content"]["application/json"]["examples"]


def test_openapi_documents_common_errors_on_every_domain_route(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    domain_operations = [
        (path, method, operation)
        for path, item in paths.items()
        if not path.startswith("/health/")
        for method, operation in item.items()
    ]
    assert domain_operations
    for path, method, operation in domain_operations:
        assert "429" in operation["responses"], f"{method.upper()} {path} sem 429"
        assert "500" in operation["responses"], f"{method.upper()} {path} sem 500"


def test_openapi_probes_do_not_document_common_errors(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    for probe in ("/health/liveness", "/health/readiness"):
        responses = paths[probe]["get"]["responses"]
        assert "429" not in responses
        assert "500" not in responses
    assert "/healthz" not in paths


def test_openapi_ai_routes_document_invalid_image(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    for path in ("/identify", "/diagnose"):
        examples = paths[path]["post"]["responses"]["400"]["content"]["application/json"]["examples"]
        assert "PLANTE_4013_INVALID_IMAGE" in examples
